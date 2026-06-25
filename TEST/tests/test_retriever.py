def test_retriever_structure():
    """Test that Retriever can be instantiated and returns correct types."""
    from app.rag.retriever import Retriever
    from app.services.vector_store import VectorStoreService

    vs = VectorStoreService()
    # Create retriever without LLM (will skip embedding)
    retriever = Retriever(vs, None)

    assert hasattr(retriever, "retrieve")
    assert hasattr(retriever, "vector_store")
    assert hasattr(retriever, "hybrid_retriever")
    assert hasattr(retriever, "bm25_retriever")
