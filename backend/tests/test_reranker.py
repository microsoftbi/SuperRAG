"""Tests for Reranker."""


def test_reranker_parse_score():
    """Test score parsing from LLM response."""
    from app.rag.reranker import Reranker
    from app.services.llm_service import LLMService

    reranker = Reranker(LLMService())

    assert reranker._parse_score("8") == 0.8
    assert reranker._parse_score("评分：7") == 0.7
    assert reranker._parse_score("10") == 1.0
    assert reranker._parse_score("0") == 0.0
    assert reranker._parse_score("不相关") == 0.0


def test_reranker_empty_results():
    """Empty results should return empty list."""
    from app.rag.reranker import Reranker
    from app.services.llm_service import LLMService

    reranker = Reranker(LLMService())
    assert reranker.rerank("test", []) == []
