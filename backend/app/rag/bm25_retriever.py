# backend/app/rag/bm25_retriever.py
"""BM25 keyword-based retriever for hybrid search."""

import json
import re
from typing import Optional

from rank_bm25 import BM25Okapi

from app.config import settings
from app.database import SessionLocal
from app.models.chunk import Chunk


class BM25Retriever:
    """BM25 keyword retriever that indexes chunks from SQLite.

    Builds BM25 index from chunk contents stored in the database.
    Used alongside vector search for hybrid retrieval.
    """

    def __init__(self):
        self._corpus: list[str] = []
        self._chunk_ids: list[str] = []
        self._metadatas: list[dict] = []
        self._bm25: Optional[BM25Okapi] = None
        self._initialized = False

    def rebuild_index(self):
        """Rebuild the BM25 index from all chunks in the database."""
        db = SessionLocal()
        try:
            chunks = db.query(Chunk).all()
            self._corpus = []
            self._chunk_ids = []
            self._metadatas = []

            for chunk in chunks:
                if not chunk.content or not chunk.content.strip():
                    continue
                self._corpus.append(chunk.content)
                self._chunk_ids.append(chunk.embedding_id or str(chunk.id))
                metadata = {}
                if chunk.metadata_json:
                    try:
                        metadata = json.loads(chunk.metadata_json)
                    except json.JSONDecodeError:
                        pass
                metadata["chunk_id"] = chunk.id
                metadata["document_id"] = chunk.document_id
                self._metadatas.append(metadata)

            if self._corpus:
                tokenized = self._tokenize_corpus(self._corpus)
                self._bm25 = BM25Okapi(tokenized)
            else:
                self._bm25 = None

            self._initialized = True
        finally:
            db.close()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize Chinese text by characters and English words."""
        text = text.lower()
        tokens = []
        tokens.extend(re.findall(r"[一-鿿]", text))
        tokens.extend(re.findall(r"[a-z0-9]+", text))
        return tokens

    def _tokenize_corpus(self, corpus: list[str]) -> list[list[str]]:
        return [self._tokenize(doc) for doc in corpus]

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        """Search with BM25 and return results.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of dicts with id, content, metadata, score keys
        """
        if not self._initialized:
            self.rebuild_index()

        if not self._bm25 or not self._corpus:
            return []

        top_k = k or settings.bm25_top_k
        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        scored = [
            (i, scores[i])
            for i in range(len(scores))
            if scores[i] > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_k]

        results = []
        for idx, score in scored:
            results.append({
                "id": self._chunk_ids[idx],
                "content": self._corpus[idx],
                "metadata": self._metadatas[idx],
                "score": float(score),
            })
        return results

    def delete_by_document(self, document_id: int):
        """Mark index as stale — will be rebuilt on next retrieve."""
        self._initialized = False
