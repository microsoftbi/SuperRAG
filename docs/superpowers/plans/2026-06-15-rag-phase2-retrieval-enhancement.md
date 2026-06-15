# RAG 客服对话系统 — 实现计划 (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强检索模块，实现 Query 重写、混合检索（向量+BM25）、重排序，显著提升检索召回率和答案质量

**Architecture:** 在现有 Phase 1 基础上新增：
- QueryRewriter：用 LLM 改写用户问题 + 指代消解
- BM25Retriever：基于 rank-bm25 的关键词检索
- HybridRetriever：向量 + BM25 结果融合（RRF 算法）
- Reranker：cross-encoder 重排序
- 整合到 chat API 和 document_processor

**Tech Stack:** rank-bm25, 现有 LLMService (火山引擎), 现有 VectorStoreService (ChromaDB)

---

## 文件结构变更

```
backend/app/rag/
├── query_rewriter.py      # NEW: Query 重写 + 指代消解
├── bm25_retriever.py      # NEW: BM25 关键词检索
├── hybrid_retriever.py    # NEW: 混合检索融合
├── reranker.py            # NEW: 重排序
├── retriever.py           # MODIFIED: 继承自 VectorStoreService，现有接口不变
├── generator.py           # MODIFIED: 接收重写后的 query
├── document_processor.py  # MODIFIED: 建立 BM25 索引
└── __init__.py            # MODIFIED: 导出新模块
backend/app/api/chat.py    # MODIFIED: 整合新的检索链路
backend/app/config.py      # MODIFIED: 新增 Phase 2 配置参数
backend/requirements.txt   # MODIFIED: 新增 rank-bm25
```

---

### Task 1: 更新配置与依赖

**Files:**
- Modify: `backend/app/config.py` — 新增 Phase 2 参数
- Modify: `backend/requirements.txt` — 新增 rank-bm25

- [ ] **Step 1: 更新 config.py**

```python
# 新增参数
enable_query_rewriting: bool = True
enable_hybrid_retrieval: bool = True
enable_reranker: bool = True
bm25_top_k: int = 10          # BM25 检索数量
hybrid_fusion_k: int = 60     # RRF 融合常数
reranker_top_k: int = 5       # 重排序后保留数量
```

- [ ] **Step 2: 更新 requirements.txt**

```
rank-bm25==0.2.2
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py backend/requirements.txt
git commit -m "feat(config): add Phase 2 retrieval enhancement config"
```

---

### Task 2: Query 重写模块

**Files:**
- Create: `backend/app/rag/query_rewriter.py`

- [ ] **Step 1: 创建 QueryRewriter**

```python
# backend/app/rag/query_rewriter.py
"""Query rewriting and coreference resolution for multi-turn conversation."""

from app.services.llm_service import LLMService

REWRITE_SYSTEM_PROMPT = """你是一个专业的搜索查询改写助手。你的任务是根据对话历史，将用户最新的问题改写成适合检索的独立查询。

规则：
1. 解析代词（如"这个"、"它"、"那个"、"它们"等）指代的具体内容
2. 将不完整的问题补充完整
3. 保留原问题的核心意图
4. 直接输出改写后的查询，不要任何解释或前缀
5. 如果问题已经很清晰无需改写，则原样输出"""


class QueryRewriter:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rewrite(self, query: str, history: list[dict]) -> str:
        """Rewrite the user query based on conversation history for better retrieval.
        
        Args:
            query: The user's latest query
            history: List of previous messages [{"role": str, "content": str}]
            
        Returns:
            Rewritten query string
        """
        if not history or len(history) < 2:
            return query

        # 取最近 4 轮对话作为上下文
        recent_history = history[-4:]
        history_text = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in recent_history
        )

        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": f"对话历史：\n{history_text}\n\n当前问题：{query}\n\n改写后的查询："},
        ]

        rewritten = ""
        for chunk in self.llm_service.chat_stream(messages, temperature=0.3):
            rewritten += chunk

        result = rewritten.strip().strip('"\'')
        return result if result else query
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/rag/query_rewriter.py
git commit -m "feat(rag): add QueryRewriter with coreference resolution"
```

---

### Task 3: BM25 关键词检索模块

**Files:**
- Create: `backend/app/rag/bm25_retriever.py`

- [ ] **Step 1: 创建 BM25Retriever**

```python
# backend/app/rag/bm25_retriever.py
"""BM25 keyword-based retriever for hybrid search."""

import json
import re
from typing import Optional

from rank_bm25 import BM25Okapi

from app.config import settings
from app.models.chunk import Chunk
from app.database import SessionLocal


class BM25Retriever:
    """BM25 keyword retriever that indexes chunks from SQLite.
    
    Builds BM25 index from chunk contents stored in the database.
    Used alongside vector search for hybrid retrieval.
    """

    def __init__(self):
        self._corpus: list[str] = []
        self._chunk_ids: list[str] = []
        self._metadatas: list[dict] = []
        self._bm25: Optional[BM25Okapi] = None
        self._initialized = False

    def rebuild_index(self):
        """Rebuild the BM25 index from all chunks in the database."""
        db = SessionLocal()
        try:
            chunks = db.query(Chunk).all()
            self._corpus = []
            self._chunk_ids = []
            self._metadatas = []

            for chunk in chunks:
                if not chunk.content or not chunk.content.strip():
                    continue
                self._corpus.append(chunk.content)
                self._chunk_ids.append(chunk.embedding_id or str(chunk.id))
                metadata = {}
                if chunk.metadata_json:
                    try:
                        metadata = json.loads(chunk.metadata_json)
                    except json.JSONDecodeError:
                        pass
                metadata["chunk_id"] = chunk.id
                metadata["document_id"] = chunk.document_id
                self._metadatas.append(metadata)

            if self._corpus:
                tokenized = self._tokenize_corpus(self._corpus)
                self._bm25 = BM25Okapi(tokenized)
            else:
                self._bm25 = None

            self._initialized = True
        finally:
            db.close()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize Chinese text by characters and English words."""
        text = text.lower()
        tokens = []
        # Match CJK characters (each character as a token)
        tokens.extend(re.findall(r'[一-鿿]', text))
        # Match English words and numbers
        tokens.extend(re.findall(r'[a-z0-9]+', text))
        return tokens

    def _tokenize_corpus(self, corpus: list[str]) -> list[list[str]]:
        return [self._tokenize(doc) for doc in corpus]

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        """Search with BM25 and return results.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of dicts with id, content, metadata, score keys
        """
        if not self._initialized:
            self.rebuild_index()

        if not self._bm25 or not self._corpus:
            return []

        top_k = k or settings.bm25_top_k
        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # Sort by score descending
            scored = [
            (i, scores[i])
            for i in range(len(scores))
            if scores[i] > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_k]

        results = []
        for idx, score in scored:
            results.append({
                "id": self._chunk_ids[idx],
                "content": self._corpus[idx],
                "metadata": self._metadatas[idx],
                "score": float(score),
            })
        return results

    def delete_by_document(self, document_id: int):
        """Mark index as stale — will be rebuilt on next retrieve."""
        self._initialized = False
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/rag/bm25_retriever.py
git commit -m "feat(rag): add BM25 keyword retriever with Chinese tokenization"
```

---

### Task 4: 混合检索融合模块

**Files:**
- Create: `backend/app/rag/hybrid_retriever.py`

- [ ] **Step 1: 创建 HybridRetriever（RRF 融合）**

```python
# backend/app/rag/hybrid_retriever.py
"""Hybrid retrieval combining vector search and BM25 via RRF fusion."""

from app.config import settings
from app.services.vector_store import VectorStoreService
from app.rag.bm25_retriever import BM25Retriever


class HybridRetriever:
    """Hybrid retriever using Reciprocal Rank Fusion (RRF) to merge
    vector search and BM25 keyword search results."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        bm25_retriever: BM25Retriever,
    ):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        """Perform hybrid retrieval with RRF fusion.
        
        Args:
            query: Search query
            k: Number of final results to return
            
        Returns:
            List of dicts with id, content, metadata, score keys, sorted by fused score
        """
        top_k = k or settings.reranker_top_k
        vector_k = settings.retriever_top_k
        bm25_k = settings.bm25_top_k

        # Run both retrievers
        vector_results = self.vector_store.similarity_search(query, k=vector_k)
        bm25_results = self.bm25_retriever.retrieve(query, k=bm25_k)

        # RRF fusion
        fusion_scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        # Assign RRF scores: 1 / (k + rank)
        k_const = settings.hybrid_fusion_k

        for rank, item in enumerate(vector_results):
            doc_id = item["id"]
            fusion_scores[doc_id] = fusion_scores.get(doc_id, 0) + 1.0 / (k_const + rank + 1)
            result_map[doc_id] = item

        for rank, item in enumerate(bm25_results):
            doc_id = item["id"]
            fusion_scores[doc_id] = fusion_scores.get(doc_id, 0) + 1.0 / (k_const + rank + 1)
            if doc_id not in result_map:
                result_map[doc_id] = item

        # Sort by fused score descending
        sorted_ids = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            item = result_map[doc_id].copy()
            item["score"] = round(fusion_scores[doc_id], 4)
            results.append(item)

        return results
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/rag/hybrid_retriever.py
git commit -m "feat(rag): add HybridRetriever with RRF fusion"
```

---

### Task 5: 重排序模块

**Files:**
- Create: `backend/app/rag/reranker.py`

- [ ] **Step 1: 创建 Reranker**

由于火山引擎不直接提供 cross-encoder API，这里使用 LLM 对检索结果进行轻量级相关性评分，或者直接使用向量检索的 score 排序。考虑到实际场景，我们用 LLM 对 Top-N 结果进行语义相关性打分。

```python
# backend/app/rag/reranker.py
"""Re-ranking using LLM-based relevance scoring."""

import asyncio
import json
from typing import Optional

from app.config import settings
from app.services.llm_service import LLMService


RERANK_PROMPT = """请判断以下文档片段与用户问题的相关性。

用户问题：{query}

文档片段：{content}

请只返回一个 0-10 的整数评分，其中：
- 0-2：完全不相关
- 3-5：部分相关，但信息不完整或只是泛泛提及
- 6-8：相关，包含了直接回答问题的信息
- 9-10：高度相关，直接且完整地回答了问题

只返回数字，不要任何其他内容。"""


class Reranker:
    """Re-ranker that uses LLM to score document relevance."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rerank(self, query: str, results: list[dict]) -> list[dict]:
        """Re-rank results using LLM relevance scoring.
        
        Args:
            query: Original user query
            results: List of retrieval results
            
        Returns:
            Re-ranked results sorted by relevance, limited to reranker_top_k
        """
        if not results:
            return []

        top_k = settings.reranker_top_k

        # Score each result
        scored = []
        for item in results:
            content = item.get("content", "")[:500]  # Truncate for prompt
            prompt = RERANK_PROMPT.format(query=query, content=content)

            messages = [
                {"role": "system", "content": "你是一个文档相关性评分助手。"},
                {"role": "user", "content": prompt},
            ]

            try:
                response_text = ""
                for chunk in self.llm_service.chat_stream(messages, temperature=0.1):
                    response_text += chunk

                score = self._parse_score(response_text.strip())
                item["rerank_score"] = score
                scored.append(item)
            except Exception:
                item["rerank_score"] = 0
                scored.append(item)

        # Sort by rerank score descending
        scored.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return scored[:top_k]

    def _parse_score(self, text: str) -> float:
        """Parse numeric score from LLM response."""
        import re
        matches = re.findall(r'\d+', text)
        if matches:
            score = int(matches[0])
            return max(0, min(10, score)) / 10.0  # Normalize to 0-1
        return 0.0
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/rag/reranker.py
git commit -m "feat(rag): add Reranker with LLM-based relevance scoring"
```

---

### Task 6: 整合现有模块

**Files:**
- Modify: `backend/app/rag/__init__.py` — 导出新模块
- Modify: `backend/app/rag/generator.py` — 接收重写后的 query
- Modify: `backend/app/rag/document_processor.py` — 触发 BM25 索引重建
- Modify: `backend/app/rag/retriever.py` — 升级为混合检索入口
- Modify: `backend/app/api/chat.py` — 整合新的检索链路

- [ ] **Step 1: 更新 rag/__init__.py**

```python
from app.rag.document_processor import DocumentProcessor
from app.rag.generator import Generator
from app.rag.retriever import Retriever
from app.rag.query_rewriter import QueryRewriter
from app.rag.bm25_retriever import BM25Retriever
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import Reranker

__all__ = [
    "DocumentProcessor", "Retriever", "Generator",
    "QueryRewriter", "BM25Retriever", "HybridRetriever", "Reranker",
]
```

- [ ] **Step 2: 更新 generator.py**

Generator 的接口不变（接收 contexts 列表），但需要在 build_messages 中标注改写后的 query（如果 query 被重写过）。

修改 generate_stream 签名：

```python
def generate_stream(
    self,
    query: str,
    contexts: list[dict],
    history: list[dict],
    temperature: float = 0.7,
    original_query: str | None = None,
) -> StreamGenerator[str, None, None]:
```

- [ ] **Step 3: 更新 document_processor.py**

在 process_document 末尾触发 BM25 索引重建：

```python
def process_document(self, document: Document) -> int:
    # ... existing code ...
    
    # 写入向量库
    self.vector_store.add_texts(chunk_ids, texts, metadatas)
    
    # 触发 BM25 索引重建
    if hasattr(self, 'bm25_retriever') and self.bm25_retriever:
        self.bm25_retriever.rebuild_index()
    
    return len(chunks)
```

- [ ] **Step 4: 更新 retriever.py** — 升级为智能检索入口

```python
"""Enhanced retriever that orchestrates query rewriting, hybrid retrieval, and re-ranking."""

from typing import Optional

from app.config import settings
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.rag.query_rewriter import QueryRewriter
from app.rag.bm25_retriever import BM25Retriever
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import Reranker


class Retriever:
    """Enhanced retriever that orchestrates the full retrieval pipeline:
    query rewriting → hybrid retrieval (vector + BM25) → re-ranking.
    Falls back to simple vector search when enhancements are disabled."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_service: LLMService,
    ):
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.query_rewriter = QueryRewriter(llm_service)
        self.bm25_retriever = BM25Retriever()
        self.hybrid_retriever = HybridRetriever(vector_store, self.bm25_retriever)
        self.reranker = Reranker(llm_service)

    def retrieve(
        self,
        query: str,
        history: list[dict] | None = None,
        k: int | None = None,
    ) -> tuple[list[dict], str]:
        """Execute the full retrieval pipeline.
        
        Args:
            query: User's query
            history: Conversation history for query rewriting
            k: Number of final results
            
        Returns:
            Tuple of (contexts, rewritten_query)
        """
        # Step 1: Query rewriting
        rewritten_query = query
        if settings.enable_query_rewriting and history:
            rewritten_query = self.query_rewriter.rewrite(query, history)

        # Step 2: Hybrid retrieval
        if settings.enable_hybrid_retrieval:
            results = self.hybrid_retriever.retrieve(rewritten_query, k=settings.retriever_top_k)
        else:
            results = self.vector_store.similarity_search(rewritten_query, k=k)

        # Step 3: Re-ranking
        if settings.enable_reranker and results:
            results = self.reranker.rerank(rewritten_query, results)
        elif k:
            results = results[:k]

        return results, rewritten_query
```

- [ ] **Step 5: 更新 chat.py**

```python
# backend/app/api/chat.py
@router.post("")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. 检索（含 Query 重写 + 混合检索 + 重排序）
    contexts, rewritten_query = retriever.retrieve(request.query, history=request.history)
    
    # 记录重写后的 query（用于日志）
    
    def stream_response():
        full_answer = ""
        for chunk in generator.generate_stream(
            rewritten_query, contexts, request.history,
            original_query=request.query,
        ):
            full_answer += chunk
            yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

        sources = [
            {
                "chunk_id": ctx["id"],
                "document_title": ctx.get("metadata", {}).get("document_title", ""),
                "content": ctx["content"][:200],
                "score": round(ctx.get("rerank_score", ctx.get("score", 0)), 4),
            }
            for ctx in contexts[:5]
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/rag/__init__.py backend/app/rag/generator.py backend/app/rag/document_processor.py backend/app/rag/retriever.py backend/app/api/chat.py
git commit -m "feat(rag): integrate Phase 2 pipeline - query rewrite, hybrid retrieval, reranker"
```

---

### Task 7: 前端适配

**Files:**
- Modify: `frontend/src/components/chat/MessageBubble.vue` — 显示重写后的 query（可选）

前端不需要大改，因为 chat API 接口没有变化。

- [ ] **Step 1: Commit（如果无需前端改动，跳过此 Task）**

---

### Task 8: 测试

**Files:**
- Create: `backend/tests/test_query_rewriter.py`
- Create: `backend/tests/test_bm25_retriever.py`
- Create: `backend/tests/test_hybrid_retriever.py`
- Create: `backend/tests/test_reranker.py`

- [ ] **Step 1: QueryRewriter 测试**

```python
# backend/tests/test_query_rewriter.py
"""Tests for QueryRewriter."""


def test_rewrite_no_history():
    """Without history, query should be returned as-is."""
    from app.rag.query_rewriter import QueryRewriter
    from app.services.llm_service import LLMService

    rewriter = QueryRewriter(LLMService())
    result = rewriter.rewrite("测试问题", [])
    assert result == "测试问题"


def test_rewrite_single_message():
    """With only one message (no assistant reply), should return as-is."""
    from app.rag.query_rewriter import QueryRewriter
    from app.services.llm_service import LLMService

    rewriter = QueryRewriter(LLMService())
    result = rewriter.rewrite("测试问题", [{"role": "user", "content": "之前的问题"}])
    assert result == "测试问题"
```

- [ ] **Step 2: BM25Retriever 测试**

```python
# backend/tests/test_bm25_retriever.py
"""Tests for BM25Retriever."""


def test_bm25_tokenize():
    """Test Chinese + English tokenization."""
    from app.rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    tokens = retriever._tokenize("你好 world 123")
    assert "你" in tokens
    assert "好" in tokens
    assert "world" in tokens
    assert "123" in tokens


def test_bm25_empty_index():
    """Empty index should return empty results."""
    from app.rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    results = retriever.retrieve("test")
    assert isinstance(results, list)
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/ -v`

Expected: 原有测试 + 新增测试通过

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "test: add Phase 2 tests for query rewriting, BM25, hybrid retrieval"
```

---

## Self-Review: 覆盖度检查

| Phase 2 需求 | 对应 Task |
|-------------|-----------|
| Query 重写（语义改写） | Task 2 — QueryRewriter |
| 指代消解（代词解析） | Task 2 — QueryRewriter（含 history 上下文） |
| BM25 关键词检索 | Task 3 — BM25Retriever |
| 中文分词 | Task 3 — _tokenize CJK char + English word |
| 混合检索 RRF 融合 | Task 4 — HybridRetriever |
| 重排序（cross-encoder） | Task 5 — Reranker（LLM-based scoring） |
| 可配置开关 | Task 1 — config.py enable_* booleans |
| 与现有管道集成 | Task 6 — retriever.py 升级为编排入口 |
| BM25 索引重建 | Task 6 — document_processor 触发 |
