# backend/app/services/vector_store.py
"""Vector store backed by Milvus Lite.

Stores both dense (embedding) vectors and sparse (BM25) vectors in the same
collection. The BM25 vectors are computed by BM25EmbeddingFunction from the
milvus-model package, which uses jieba for Chinese tokenization.

Collection schema:
  - id (INT64, primary)
  - chunk_id (VARCHAR)     — original chunk UUID
  - text (VARCHAR)         — chunk content
  - dense (FLOAT_VECTOR)   — embedding vector
  - sparse (SPARSE_FLOAT_VECTOR) — BM25 sparse vector
  - document_id (INT64)    — for filtering/access control
  - document_title (VARCHAR)
  - chunk_index (INT64)
"""

import json
import logging

import numpy as np
from pymilvus import MilvusClient, DataType, AnnSearchRequest, RRFRanker
from scipy.sparse import csr_array

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sprag_docs"


class VectorStoreService:
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.client = MilvusClient(uri=settings.milvus_lite_uri)
        self._ensure_collection()

    def _ensure_collection(self):
        if self.client.has_collection(COLLECTION_NAME):
            self.client.load_collection(COLLECTION_NAME)
            return
        schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="chunk_id", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name="document_id", datatype=DataType.INT64)
        schema.add_field(field_name="document_title", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)

        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="dense", index_type="FLAT", metric_type="COSINE")
        index_params.add_index(field_name="sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="IP")

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(COLLECTION_NAME)
        logger.info("Created Milvus collection %s (dim=%d)", COLLECTION_NAME, settings.embedding_dim)

    def add_texts(self, ids: list[str], texts: list[str], metadatas: list[dict]):
        """Insert chunks with dense vectors (and BM25 sparse vectors if available)."""
        dense_embs = self.llm_service.embed(texts) if self.llm_service else [None] * len(texts)
        sparse_embs = self._compute_sparse_batch(texts)

        data = []
        for i, (chunk_id, text, meta) in enumerate(zip(ids, texts, metadatas)):
            sparse_vec = sparse_embs[i] if sparse_embs is not None else None
            row = {
                "chunk_id": chunk_id,
                "text": text,
                "dense": dense_embs[i] if dense_embs[i] is not None else [0.0] * settings.embedding_dim,
                "sparse": sparse_vec if sparse_vec is not None else {},
                "document_id": meta.get("document_id", 0),
                "document_title": meta.get("document_title", ""),
                "chunk_index": meta.get("chunk_index", 0),
            }
            data.append(row)

        for row in data:
            self.client.insert(COLLECTION_NAME, [row])
        logger.info("Inserted %d chunks into Milvus", len(data))

    def _compute_sparse_batch(self, texts: list[str]):
        """Compute BM25 sparse vectors for a batch of texts.

        Falls back to None if BM25 retriever is not yet initialized.
        Returns list of csr_array, each with shape (1, dim).
        """
        try:
            from app.rag.bm25_retriever import _bm25_ef
            if _bm25_ef is None:
                return [None] * len(texts)
            embs = _bm25_ef.encode_documents(texts)
            # embs is csr_array with shape (N, M); split into N vectors each (1, M)
            return [embs[i:i+1] for i in range(embs.shape[0])]
        except Exception:
            return [None] * len(texts)

    # ── Dense search ──

    def similarity_search(
        self, query: str, k: int | None = None,
        where_filter: dict | None = None,
    ) -> list[dict]:
        """Pure dense vector search (fallback when hybrid is disabled)."""
        top_k = k or settings.retriever_top_k
        query_emb = self.llm_service.embed([query])[0]
        expr = self._build_filter_expr(where_filter)

        results = self.client.search(
            collection_name=COLLECTION_NAME,
            data=[query_emb],
            anns_field="dense",
            limit=top_k,
            filter=expr,
            output_fields=["chunk_id", "text", "document_id", "document_title", "chunk_index"],
        )
        return self._flatten_results(results)

    # ── Hybrid search (dense + BM25 sparse) ──

    def hybrid_search(
        self, query: str, query_sparse,
        k: int | None = None,
        where_filter: dict | None = None,
    ) -> list[dict]:
        """Hybrid search: dense (cosine) + sparse (IP) fused via RRF."""
        top_k = k or settings.retriever_top_k
        query_emb = self.llm_service.embed([query])[0]
        expr = self._build_filter_expr(where_filter)

        req_dense = AnnSearchRequest(
            data=[query_emb],
            anns_field="dense",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k * 2,
            expr=expr,
        )
        req_sparse = AnnSearchRequest(
            data=[query_sparse],
            anns_field="sparse",
            param={"metric_type": "IP", "params": {}},
            limit=top_k * 2,
            expr=expr,
        )

        results = self.client.hybrid_search(
            collection_name=COLLECTION_NAME,
            reqs=[req_dense, req_sparse],
            ranker=RRFRanker(),
            limit=top_k,
            output_fields=["chunk_id", "text", "document_id", "document_title", "chunk_index"],
        )
        return self._flatten_results(results)

    # ── BM25 sparse search only ──

    def sparse_search(
        self, query_sparse, k: int | None = None,
        where_filter: dict | None = None,
    ) -> list[dict]:
        """Pure BM25 sparse search."""
        top_k = k or settings.retriever_top_k
        expr = self._build_filter_expr(where_filter)

        results = self.client.search(
            collection_name=COLLECTION_NAME,
            data=[query_sparse],
            anns_field="sparse",
            limit=top_k,
            filter=expr,
            output_fields=["chunk_id", "text", "document_id", "document_title", "chunk_index"],
        )
        return self._flatten_results(results)

    # ── Deletion ──

    def delete_by_document(self, document_id: int):
        self.client.delete(COLLECTION_NAME, filter=f"document_id == {document_id}")

    def delete_by_ids(self, ids: list[str]):
        if not ids:
            return
        # Milvus delete by expr — escape single quotes in chunk_id values
        ids_escaped = [cid.replace("'", "\\'") for cid in ids]
        quoted = [f"'{cid}'" for cid in ids_escaped]
        expr = f"chunk_id in [{', '.join(quoted)}]"
        self.client.delete(COLLECTION_NAME, filter=expr)

    # ── Read helpers ──

    def get_document_chunks(self, document_id: int) -> list[dict]:
        """查询指定文档的所有分块（按 chunk_index 排序）。"""
        results = self.client.query(
            collection_name=COLLECTION_NAME,
            filter=f"document_id == {document_id}",
            output_fields=["chunk_id", "text", "chunk_index", "document_title"],
        )
        items = []
        for r in results:
            items.append({
                "chunk_id": r.get("chunk_id", ""),
                "chunk_index": r.get("chunk_index", 0),
                "content": r.get("text", ""),
                "metadata": {
                    "document_title": r.get("document_title", ""),
                },
            })
        items.sort(key=lambda x: x["chunk_index"])
        return items

    def get_chunk_count(self) -> int:
        results = self.client.query(
            collection_name=COLLECTION_NAME,
            output_fields=["count(*)"],
        )
        return results[0]["count(*)"] if results else 0

    # ── Internal helpers ──

    def _build_filter_expr(self, where_filter: dict | None) -> str:
        if not where_filter:
            return ""
        # ChromaDB style: {"document_id": {"$in": [1, 2, 3]}}
        if "document_id" in where_filter:
            clause = where_filter["document_id"]
            if isinstance(clause, dict) and "$in" in clause:
                vals = clause["$in"]
                if vals:
                    return f"document_id in [{', '.join(str(v) for v in vals)}]"
        return ""

    def _flatten_results(self, results) -> list[dict]:
        items = []
        for hits in results:
            for hit in hits:
                fields = hit.get("entity", {}) or hit
                items.append({
                    "id": fields.get("chunk_id", str(hit.get("id", ""))),
                    "content": fields.get("text", ""),
                    "metadata": {
                        "document_id": fields.get("document_id", 0),
                        "document_title": fields.get("document_title", ""),
                        "chunk_index": fields.get("chunk_index", 0),
                    },
                    "score": round(hit.get("distance", 0), 4),
                })
        return items
