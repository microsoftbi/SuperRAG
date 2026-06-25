"""Tests for BM25Retriever."""


def test_bm25_initial_state():
    """New retriever should start uninitialized."""
    from app.rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    assert not retriever.initialized


def test_bm25_jieba_tokenization():
    """Test that jieba-based tokenization splits Chinese words correctly."""
    from milvus_model.sparse.bm25 import build_default_analyzer

    analyzer = build_default_analyzer(language="zh")
    tokens = analyzer("数据中心建设方案包括服务器")
    # jieba should produce meaningful words, not single chars
    assert "数据中心" in tokens
    assert "建设" in tokens
    assert "方案" in tokens
    assert "服务器" in tokens
