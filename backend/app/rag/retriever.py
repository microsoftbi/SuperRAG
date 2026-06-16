# backend/app/rag/retriever.py
"""Enhanced retriever that orchestrates query rewriting, hybrid retrieval, and re-ranking."""

from app.config import settings
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.bm25_retriever import BM25Retriever
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.query_rewriter import QueryRewriter
from app.rag.reranker import Reranker


class Retriever:
    """Enhanced retriever that orchestrates the full retrieval pipeline:
    query rewriting -> hybrid retrieval (vector + BM25) -> re-ranking.
    Falls back to simple vector search when enhancements are disabled.
    """

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
        doc_ids: list[int] | None = None,
    ) -> tuple[list[dict], str]:
        """Execute the full retrieval pipeline.

        Args:
            query: User's query
            history: Conversation history for query rewriting
            k: Number of final results
            doc_ids: Filter by document IDs (for KB access control)

        Returns:
            Tuple of (contexts, rewritten_query)
        """
        # Step 1: Query rewriting
        rewritten_query = query
        if settings.enable_query_rewriting and history:
            rewritten_query = self.query_rewriter.rewrite(query, history)

        # Step 2: Hybrid retrieval
        if settings.enable_hybrid_retrieval:
            results = self.hybrid_retriever.retrieve(
                rewritten_query, k=settings.retriever_top_k, doc_ids=doc_ids,
            )
        else:
            where_filter = {"document_id": {"$in": doc_ids}} if doc_ids else None
            results = self.vector_store.similarity_search(rewritten_query, k=k, where_filter=where_filter)

        # Step 3: Re-ranking
        if settings.enable_reranker and results:
            results = self.reranker.rerank(rewritten_query, results)
        elif k:
            results = results[:k]

        return results, rewritten_query
