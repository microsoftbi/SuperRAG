"""Tests for QueryRewriter."""


def test_rewrite_no_history():
    """Without history, query should be returned as-is."""
    from app.rag.query_rewriter import QueryRewriter
    from app.services.llm_service import LLMService

    rewriter = QueryRewriter(LLMService())
    result = rewriter.rewrite("测试问题", [])
    assert result == "测试问题"


def test_rewrite_single_message():
    """With only one message (no assistant reply), should return as-is."""
    from app.rag.query_rewriter import QueryRewriter
    from app.services.llm_service import LLMService

    rewriter = QueryRewriter(LLMService())
    result = rewriter.rewrite(
        "测试问题",
        [{"role": "user", "content": "之前的问题"}],
    )
    assert result == "测试问题"
