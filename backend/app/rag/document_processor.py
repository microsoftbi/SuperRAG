import logging
import os
import uuid
from pathlib import Path

import docx
import markdown
import pypdf
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models.document import Document
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

    def _read_file(self, file_path: str) -> str:
        return Path(file_path).read_text(encoding="utf-8")

    def extract_text(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext == ".md":
            return self._extract_md(file_path)
        elif ext in (".html", ".htm"):
            return self._extract_html(file_path)
        elif ext == ".txt":
            return self._read_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, file_path: str) -> str:
        reader = pypdf.PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    def _extract_md(self, file_path: str) -> str:
        raw = self._read_file(file_path)
        html = markdown.markdown(raw)
        return BeautifulSoup(html, "html.parser").get_text()

    def _extract_html(self, file_path: str) -> str:
        raw = self._read_file(file_path)
        return BeautifulSoup(raw, "html.parser").get_text()

    def process_document(self, document: Document) -> int:
        file_path = document.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("Processing document %s (id=%d)", document.title, document.id)
        raw_text = self.extract_text(file_path)
        if not raw_text.strip():
            logger.warning("Empty text extracted from %s", file_path)
            return 0

        chunks = self.text_splitter.split_text(raw_text)
        chunk_ids = []
        texts = []
        metadatas = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            texts.append(chunk_text)
            metadatas.append({
                "document_id": document.id,
                "document_title": document.title,
                "chunk_index": i,
                "doc_type": document.doc_type,
                "category": document.category,
            })

        self.vector_store.add_texts(chunk_ids, texts, metadatas)
        logger.info("Document %s processed into %d chunks", document.title, len(chunks))
        return len(chunks)
