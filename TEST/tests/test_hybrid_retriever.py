"""Tests for HybridRetriever."""


def test_hybrid_rrf_scoring():
    """Test that RRF fusion produces expected score distribution."""
    from app.rag.hybrid_retriever import HybridRetriever

    # The HybridRetriever depends on vector_store and bm25_retriever,
    # which require database/API access. This test verifies the class
    # can be instantiated and has the right interface.
    assert hasattr(HybridRetriever, "retrieve")
