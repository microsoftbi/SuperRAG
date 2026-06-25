# RAG 响应速度优化方案

## 一、现状分析

### 完整请求链路（RAG 模式）

```
用户提问
  │
  ├─ ① Chat API 入口
  │     ├─ Query 改写（LLM 调用）  ─── 有历史时才执行
  │     ├─ 创建 log（SQLite INSERT）
  │     └─ 进入 Agent 流
  │
  ├─ ② DeepAgent 流式响应
  │     ├─ Agent 思考（LLM 调用 #1：读系统提示词，决定调哪个工具）
  │     │   └─ SqliteSaver 写入 checkpoint
  │     ├─ 调用 search_knowledge_base / search_knowledge_graph
  │     │   ├─ RAG: Milvus hybrid_search → BM25 + 向量
  │     │   ├─ KG: Neo4j 图遍历 → SQLite 查 chunk
  │     │   ├─ Reranker（LLM 调用 #2~#6：每条结果打分，串行 5 次！）
  │     │   └─ SqliteSaver 写入 checkpoint
  │     └─ Agent 生成回答（LLM 调用 #7）
  │         └─ SqliteSaver 写入 checkpoint
  │
  ├─ ③ 流结束后
  │     ├─ 重新跑 KG 检索（重复 ② 中的 KG 工作）
  │     ├─ 重新跑 RAG 检索（重复 ② 中的 RAG 工作）
  │     └─ 写入 log（SQLite UPDATE）
  │
  └─ ④ 推送 sources + DONE
```

### 瓶颈诊断

| # | 瓶颈 | 耗时估计 | 严重程度 |
|:--:|---|---|:--:|
| A | **Reranker 串行 LLM 调用** — 每轮检索结果 5 条,每条单独调一次 LLM 打分 | 5×1.5s = **7.5s** | 🔴 致命 |
| B | **Agent 多轮 LLM 调用** — 思考+工具+回答,最少 2 轮(无工具)、最多 3+ 轮 | 2×1.5s = **3s** | 🟠 高 |
| C | **流结束后重复检索** — Agent 工具已经查过一次,流结束后又查一次 | **2s** | 🟠 高 |
| D | **SqliteSaver 频繁写 checkpoint** — 每轮都写 SQLite | **0.5-1s** | 🟡 中 |
| E | **多段 SQLite 写入** — INSERT log + 可能 2 次 UPDATE | **0.3s** | 🟢 低 |
| F | **Neo4j 网络延迟** — KG 跨进程查询 | **0.5s** | 🟢 低 |

**合计估计**: ~10-15s（其中 80% 是 LLM 串行调用）

---

## 二、优化方案

### 方案 A（推荐）: 去掉 LLM Reranker → 改用 Score 排序

**当前问题**: `Reranker.rerank()` 对 5 条结果逐条调 LLM 打分,5 次串行 LLM 调用。

**改造**:
```python
# 当前（5 次 LLM 调用）:
for item in results:
    score = llm.chat_stream([RERANK_PROMPT])  # 5 次!
    item["rerank_score"] = score

# 改为（0 次 LLM 调用）:
# 直接用 Milvus 返回的 distance / BM25 分数排序
```

**收益**: -7.5s（节省 50% 总时间）
**风险**: 排序精度略降,但对大多数问答场景足够
**改动**: 仅改 `reranker.py`

---

### 方案 B: 消除流结束后重复检索

**当前问题**: `chat.py` 第 230-269 行,流结束后重新跑 KG + RAG 检索来生成 sources。

但 Agent 工具(`search_knowledge_base` / `search_knowledge_graph`)已经把结果写进了 `_current_sources`。

**改造**:
```python
# 流结束后直接用 _current_sources，不再重新检索
sources = get_collected_sources()  # 工具已收集
if not sources:
    # 仅在没有工具调用时 fallback
    ...
```

**收益**: -2s
**改动**: 改 `chat.py` 第 230-269 行

---

### 方案 C: 跳过首轮 Query 改写

**当前问题**: 即使没有历史对话,`retriever.retrieve()` 仍然初始化 QueryRewriter(调 LLM 不做事)。

**改造**: 在 `retriever.py` 里提前判断:

```python
# retrieve() 中
if settings.enable_query_rewriting and history:
    rewritten_query = self.query_rewriter.rewrite(query, history)
# 无历史时直接跳过
```

**收益**: -0s（已做,不浪费）,但防止未来误用
**改动**: 无需改动

---

### 方案 D: 合并 SQLite 写入

**当前问题**: log 写入分 3 段:
1. INSERT(初始)
2. UPDATE sources(流结束后)
3. UPDATE answer/latency(最终)

**改造**: 合并为 1 次:

```python
# 先在内存构建,最后一次性写入
log_entry = ConversationLog(
    query=..., answer=full_answer, sources=json.dumps(sources),
    latency_ms=elapsed, ...
)
db.add(log_entry)
db.commit()  # 仅 1 次
```

**收益**: -0.2s
**改动**: 改 `chat.py` RAG 流结束后逻辑

---

### 方案 E: Agent 工具结果直接作为 sources

**当前问题**: DeepAgent 工具调用后,`_current_sources` 已经包含了检索结果。但 chat.py 没利用它,而是重新检索。

**结合方案 B**,工具结果直接映射到前端 sources:

```python
# 流结束后:
sources = get_collected_sources()
for s in sources:
    if s["type"] == "rag":
        sources_for_frontend.append({
            "chunk_id": s["chunk_id"],
            "document_title": s["document_title"],
            "content": s["content"][:200],
            "score": s["score"],
            "type": "rag",
        })
```

**收益**: 消除冗余检索

---

## 三、推荐实施顺序

| 优先级 | 方案 | 收益 | 改动量 | 风险 |
|:--:|:---|---:|:---:|:---:|
| P0 | **A: 去掉 LLM Reranker** | **-7.5s** | 1 文件 ~50 行 | 低(排序略降) |
| P1 | **B + E: 消除重复检索** | **-2s** | 1 文件 ~30 行 | 低 |
| P2 | **D: 合并 SQLite 写入** | **-0.2s** | 1 文件 ~20 行 | 低 |

**预计优化后响应时间**: 10-15s → **2-4s**

---

## 四、效果验证方法

1. 用同一个简单问题("你好")测试 3 次,取平均时间
2. 在 `chat.py` 加 `time.time()` 打点,观察各阶段耗时
3. 确认 Reranker 移除后回答质量没有明显下降

---

## 待确认

1. **方案 A 是否接受？** 去掉 LLM Reranker,用 Milvus 原始分数排序。(推荐)
   - 替代方案 A2:用轻量 cross-encoder 模型替换 LLM,但需额外部署
2. **方案 B 是否接受？** Agent 工具结果直接作为前端 sources,不重复检索。(推荐)
3. **方案 D 是否顺带做？** 合并 SQLite 写入。
