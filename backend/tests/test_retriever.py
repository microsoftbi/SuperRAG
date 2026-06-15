def test_retriever_returns_list():
    from app.services.llm_service import LLMService
    from app.services.vector_store import VectorStoreService
    from app.rag.retriever import Retriever

    llm = LLMService()
    vs = VectorStoreService(llm)
    retriever = Retriever(vs, llm)

    results, rewritten_query = retriever.retrieve("test query", k=3)
    assert isinstance(results, list)
    assert isinstance(rewritten_query, str)
