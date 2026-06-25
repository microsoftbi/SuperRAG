"""Tests for Reranker — batch scoring."""


def test_reranker_parse_batch_scores():
    """Test batch score parsing from LLM response."""
    from app.rag.reranker import Reranker
    from app.services.llm_service import LLMService

    reranker = Reranker(LLMService())

    # 正常格式
    text = "片段1: 8\n片段2: 3\n片段3: 10"
    scores = reranker._parse_batch_scores(text, 3)
    assert scores == [0.8, 0.3, 1.0]

    # 缺项 → 默认 0.0
    text2 = "片段1: 9"
    scores2 = reranker._parse_batch_scores(text2, 3)
    assert scores2[0] == 0.9
    assert scores2[1] == 0.0
    assert scores2[2] == 0.0

    # 越界索引 → 忽略
    text3 = "片段1: 5\n片段99: 10"
    scores3 = reranker._parse_batch_scores(text3, 1)
    assert scores3 == [0.5]

    # 中文冒号
    text4 = "片段1：7\n片段2：4"
    scores4 = reranker._parse_batch_scores(text4, 2)
    assert scores4 == [0.7, 0.4]

    # 纯数字格式
    text5 = "1: 6\n2: 8"
    scores5 = reranker._parse_batch_scores(text5, 2)
    assert scores5 == [0.6, 0.8]


def test_reranker_empty_results():
    """Empty results should return empty list."""
    from app.rag.reranker import Reranker
    from app.services.llm_service import LLMService

    reranker = Reranker(LLMService())
    assert reranker.rerank("test", []) == []
