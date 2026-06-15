import tempfile
from pathlib import Path
import pytest


def test_extract_text_from_txt():
    from app.rag.document_processor import DocumentProcessor
    from app.services.vector_store import VectorStoreService
    from app.services.llm_service import LLMService

    llm = LLMService()
    vs = VectorStoreService(llm)
    dp = DocumentProcessor(vs)

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("这是测试文档内容。\n第二行内容。")
        f.flush()
        text = dp.extract_text(f.name)
        assert "这是测试文档内容" in text
        assert "第二行内容" in text
    Path(f.name).unlink()


def test_extract_text_unsupported():
    from app.rag.document_processor import DocumentProcessor
    from app.services.vector_store import VectorStoreService
    from app.services.llm_service import LLMService

    llm = LLMService()
    vs = VectorStoreService(llm)
    dp = DocumentProcessor(vs)

    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
        f.write("test")
        f.flush()
        with pytest.raises(ValueError, match="Unsupported file type"):
            dp.extract_text(f.name)
    Path(f.name).unlink()
