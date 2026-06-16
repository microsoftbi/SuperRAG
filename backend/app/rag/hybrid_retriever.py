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

    def retrieve(self, query: str, k: int | None = None,
                 doc_ids: list[int] | None = None) -> list[dict]:
        """Perform hybrid retrieval with RRF fusion.

        Args:
            query: Search query
            k: Number of final results to return
            doc_ids: Filter by document IDs (for KB access control)

        Returns:
            List of dicts with id, content, metadata, score keys, sorted by fused score
        """
        top_k = k or settings.reranker_top_k
        vector_k = settings.retriever_top_k
        bm25_k = settings.bm25_top_k

        where_filter = {"document_id": {"$in": doc_ids}} if doc_ids else None
        vector_results = self.vector_store.similarity_search(query, k=vector_k, where_filter=where_filter)
        bm25_results = self.bm25_retriever.retrieve(query, k=bm25_k, doc_ids=doc_ids)

        fusion_scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

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

        sorted_ids = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            item = result_map[doc_id].copy()
            item["score"] = round(fusion_scores[doc_id], 4)
            results.append(item)

        return results
