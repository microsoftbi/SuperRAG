# backend/app/rag/bm25_retriever.py
"""BM25 keyword retrieval using milvus-model's BM25EmbeddingFunction.

Uses language='zh' (jieba Chinese tokenization) for better term segmentation.
The BM25 index is stored inside BM25EmbeddingFunction (IDF dict in memory) and
sparse vectors are persisted in Milvus Lite.

Architecture:
  1. BM25EmbeddingFunction.fit(corpus) — builds IDF dictionary
  2. BM25EmbeddingFunction.encode_documents(texts) → sparse vectors → Milvus
  3. BM25EmbeddingFunction.encode_queries(query) → sparse vector → Milvus search
"""

import logging
import threading

import numpy as np
from milvus_model.sparse import BM25EmbeddingFunction
from milvus_model.sparse.bm25 import build_default_analyzer

logger = logging.getLogger(__name__)

# Module-level singleton: BM25EmbeddingFunction shared across all requests.
_bm25_ef = None
_corpus_size = 0
_bm25_initialized = False  # module-level flag, not per-instance

# Background rebuild scheduling
_rebuild_pending = False
_rebuild_lock = threading.Lock()


class BM25Retriever:
    """BM25 retriever backed by BM25EmbeddingFunction (milvus-model).

    Rebuilds are done asynchronously so uploads don't block.
    """

    def __init__(self):
        global _bm25_ef
        if _bm25_ef is None:
            analyzer = build_default_analyzer(language="zh")
            _bm25_ef = BM25EmbeddingFunction(analyzer=analyzer)
        self._ef = _bm25_ef

    @property
    def initialized(self):
        return _bm25_initialized

    def rebuild_index(self, vector_store=None):
        """同步重建 BM25 索引（上传时调用改为异步）。"""
        if vector_store is None:
            global _bm25_initialized
            _bm25_initialized = False
            return
        self._do_rebuild(vector_store)

    def _do_rebuild(self, vector_store):
        """实际执行重建，同时重新计算所有文档的稀疏向量。"""
        global _corpus_size, _bm25_initialized
        all_texts = self._get_all_texts(vector_store)
        if not all_texts:
            logger.warning("No texts to build BM25 index")
            _bm25_initialized = False
            return
        self._ef.fit(all_texts)
        _corpus_size = len(all_texts)
        _bm25_initialized = True
        logger.info("BM25 index rebuilt: %d docs, %d terms", _corpus_size, self._ef.dim)

        # 重建后重新计算所有文档的稀疏向量并更新到 Milvus
        try:
            self._update_sparse_vectors(vector_store, all_texts)
        except Exception as e:
            logger.error("Failed to update sparse vectors after rebuild: %s", e)

    def _update_sparse_vectors(self, vector_store, texts: list[str]):
        """重新计算并更新 Milvus 中所有文档的稀疏向量。"""
        if not _bm25_initialized or not texts:
            return

        # 查询所有文档（不查 dense 向量字段，避免格式问题）
        results = vector_store.client.query(
            collection_name="sprag_docs",
            output_fields=["id", "chunk_id", "text", "document_id",
                           "document_title", "chunk_index"],
            limit=100000,
        )
        if not results:
            logger.warning("_update_sparse_vectors: query returned 0 results, nothing to update")
            return

        logger.info("_update_sparse_vectors: query returned %d rows, updating...", len(results))

        # 获取稠密向量维度
        from app.config import settings
        dim = settings.embedding_dim

        # 按 text 分组（相同 text 的 chunk 共享同一个稀疏向量）
        text_groups: dict[str, list[dict]] = {}
        for r in results:
            txt = r.get("text", "")
            if txt:
                text_groups.setdefault(txt, []).append(r)

        texts_list = list(text_groups.keys())
        sparse_embs = self._ef.encode_documents(texts_list)

        # 批量 upsert（补全所有必填字段）
        batch = []
        for i, text in enumerate(texts_list):
            if i >= sparse_embs.shape[0]:
                continue
            vec = sparse_embs[i:i+1]
            for row in text_groups[text]:
                row["sparse"] = vec
                row["dense"] = [0.0] * dim  # 补零向量
                batch.append(dict(row))
                if len(batch) >= 100:
                    vector_store.client.upsert(collection_name="sprag_docs", data=batch)
                    batch = []

        if batch:
            vector_store.client.upsert(collection_name="sprag_docs", data=batch)

        logger.info("Updated sparse vectors for %d rows in Milvus", len(results))

    def rebuild_async(self, vector_store):
        """触发异步后台重建，不阻塞调用者。"""
        global _rebuild_pending
        with _rebuild_lock:
            if _rebuild_pending:
                logger.info("BM25 rebuild already scheduled, skipping")
                return
            _rebuild_pending = True

        def _bg():
            global _rebuild_pending
            try:
                self._do_rebuild(vector_store)
            except Exception as e:
                logger.error("BM25 async rebuild failed: %s", e)
            finally:
                with _rebuild_lock:
                    _rebuild_pending = False

        t = threading.Thread(target=_bg, daemon=True)
        t.start()
        logger.info("BM25 async rebuild triggered")

    def _get_all_texts(self, vector_store):
        try:
            results = vector_store.client.query(
                collection_name="sprag_docs",
                output_fields=["text"],
                limit=100000,
            )
            return [r["text"] for r in results if r.get("text")]
        except Exception as e:
            logger.error("Failed to read texts from Milvus: %s", e)
            return []

    def compute_sparse(self, texts: list[str]) -> list:
        if not _bm25_initialized:
            logger.warning("BM25 not initialized, cannot compute sparse vectors")
            return [None] * len(texts)
        try:
            embs = self._ef.encode_documents(texts)
            return list(embs)
        except Exception as e:
            logger.error("BM25 encode failed: %s", e)
            return [None] * len(texts)

    def encode_query(self, query: str):
        if not _bm25_initialized:
            logger.warning("BM25 not initialized, returning empty sparse")
            from scipy.sparse import csr_array
            return csr_array(([], ([], [])), shape=(1, 0))
        return self._ef.encode_queries([query])

    def get_dim(self):
        return self._ef.dim if _bm25_initialized else 0

    def delete_by_document(self, document_id: int):
        """删除文档后触发异步重建。"""
        global _bm25_initialized
        _bm25_initialized = False
