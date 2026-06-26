"""Hybrid retrieval with detailed debug info.

Performs two independent searches (dense + BM25 sparse), fuses via RRF in Python,
and returns both the fused results and the detail dict for debugging.
"""

import logging

from app.config import settings
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# RRF constant (same default as Milvus RRFRanker)
_RRF_K = 60


class HybridRetriever:
    """Hybrid retriever with per-source debug detail."""

    def __init__(self, vector_store: VectorStoreService, bm25_retriever=None):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query: str, k: int | None = None,
                 doc_ids: list[int] | None = None) -> list[dict]:
        """Perform hybrid retrieval and return fused results only."""
        results, _ = self.retrieve_with_detail(query, k=k, doc_ids=doc_ids)
        return results

    def retrieve_with_detail(self, query: str, k: int | None = None,
                              doc_ids: list[int] | None = None) -> tuple[list[dict], dict]:
        """Perform hybrid retrieval with detailed debug info.

        Runs dense and sparse searches independently, fuses via RRF in Python,
        and returns both the fused results and a detail dict containing:
          {dense: [...], sparse: [...], fused: [...]}

        Returns:
            (fused_results, detail_dict)
        """
        top_k = k or settings.reranker_top_k
        where_filter = {"document_id": {"$in": doc_ids}} if doc_ids else None

        query_sparse = self.bm25_retriever.encode_query(query) if self.bm25_retriever else None
        bm25_ok = query_sparse is not None and self.bm25_retriever.initialized

        if not bm25_ok:
            # BM25 未初始化 → 降级为纯稠密检索
            logger.warning("BM25 not initialized, falling back to dense-only search")
            results = self.vector_store.similarity_search(
                query, k=top_k, where_filter=where_filter,
            )
            return results, {"dense": results, "sparse": [], "fused": results}

        # ── 两次独立检索 ──
        dense_results = self.vector_store.similarity_search(
            query, k=top_k * 2, where_filter=where_filter,
        )
        sparse_results = self.vector_store.sparse_search(
            query_sparse, k=top_k * 2, where_filter=where_filter,
        )

        # ── Python RRF 融合 ──
        rrf_scores = {}
        for rank, item in enumerate(dense_results):
            cid = item["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank + 1)
        for rank, item in enumerate(sparse_results):
            cid = item["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank + 1)

        # 按 RRF 得分排序
        ranked_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

        # 构建融合结果（合并元数据）
        item_map = {}
        for item in dense_results:
            item_map[item["id"]] = item
        for item in sparse_results:
            if item["id"] not in item_map:
                item_map[item["id"]] = item

        fused_results = []
        for cid in ranked_ids[:top_k]:
            item = dict(item_map.get(cid, {}))
            item["score"] = round(rrf_scores[cid], 4)
            fused_results.append(item)

        # 构建 detail（精简内容以节省 payload）
        def _shorten(items, max_items=10):
            return [{
                "id": it["id"],
                "content": it.get("content", "")[:120],
                "score": round(it.get("score", 0), 4),
            } for it in items[:max_items]]

        detail = {
            "dense": _shorten(dense_results),
            "sparse": _shorten(sparse_results),
            "fused": _shorten(fused_results),
        }

        logger.info("HybridRetriever: dense=%d sparse=%d fused=%d",
                     len(dense_results), len(sparse_results), len(fused_results))
        return fused_results, detail
