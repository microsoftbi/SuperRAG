"""Tests for BM25Retriever."""


def test_bm25_tokenize():
    """Test Chinese + English tokenization."""
    from app.rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    tokens = retriever._tokenize("你好 world 123")
    assert "你" in tokens
    assert "好" in tokens
    assert "world" in tokens
    assert "123" in tokens


def test_bm25_initial_state():
    """New retriever should start uninitialized."""
    from app.rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    assert not retriever._initialized
    assert retriever._corpus == []
    assert retriever._bm25 is None
