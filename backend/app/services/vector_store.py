import chromadb
from chromadb.config import Settings

from app.config import settings
from app.services.llm_service import LLMService


COLLECTION_NAME = "sprag_docs"


class VectorStoreService:
    def __init__(self, llm_service: LLMService):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.llm_service = llm_service
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_texts(self, ids: list[str], texts: list[str], metadatas: list[dict]):
        embeddings = self.llm_service.embed(texts)
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def similarity_search(
        self, query: str, k: int | None = None,
        where_filter: dict | None = None,
    ) -> list[dict]:
        top_k = k or settings.retriever_top_k
        query_embedding = self.llm_service.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        if not results["ids"]:
            return []

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],
            })
        return items

    def delete_by_document(self, document_id: int):
        self.collection.delete(where={"document_id": document_id})

    def delete_by_ids(self, ids: list[str]):
        self.collection.delete(ids=ids)

    def get_document_chunks(self, document_id: int) -> list[dict]:
        """查询 ChromaDB 中指定文档的所有分块（按 chunk_index 排序）。"""
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        if not results["ids"]:
            return []
        items = []
        # ChromaDB .get() 返回扁平列表（不同于 .query() 的嵌套列表）
        for i in range(len(results["ids"])):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            items.append({
                "chunk_id": results["ids"][i],
                "chunk_index": meta.get("chunk_index", 0) if isinstance(meta, dict) else 0,
                "content": results["documents"][i],
                "metadata": meta if isinstance(meta, dict) else {},
            })
        items.sort(key=lambda x: x["chunk_index"])
        return items
