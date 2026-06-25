# backend/app/rag/hybrid_retriever.py
"""Hybrid retrieval delegating to VectorStoreService.hybrid_search.

Dense + BM25 sparse hybrid search via Milvus's hybrid_search with RRF fusion.
"""

import logging

from app.config import settings
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever using Milvus hybrid_search (dense + BM25 sparse)."""

    def __init__(self, vector_store: VectorStoreService, bm25_retriever=None):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query: str, k: int | None = None,
                 doc_ids: list[int] | None = None) -> list[dict]:
        """Perform hybrid retrieval via Milvus hybrid_search.

        Args:
            query: Search query (used for dense embedding)
            k: Number of final results
            doc_ids: Filter by document IDs

        Returns:
            List of dicts with id, content, metadata, score keys
        """
        top_k = k or settings.reranker_top_k
        where_filter = {"document_id": {"$in": doc_ids}} if doc_ids else None

        # Compute BM25 sparse vector for query
        query_sparse = self.bm25_retriever.encode_query(query) if self.bm25_retriever else None

        if query_sparse is not None and self.bm25_retriever.initialized:
            results = self.vector_store.hybrid_search(
                query, query_sparse, k=top_k, where_filter=where_filter,
            )
        else:
            # BM25 not available → fall back to dense-only
            logger.warning("BM25 not initialized, falling back to dense-only search")
            results = self.vector_store.similarity_search(
                query, k=top_k, where_filter=where_filter,
            )

        return results
