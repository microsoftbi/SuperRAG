import chromadb
from chromadb.config import Settings
from app.config import settings
from app.services.llm_service import LLMService


class VectorStoreService:
    def __init__(self, llm_service: LLMService):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.llm_service = llm_service
        self.collection = self.client.get_or_create_collection(
            name="sprag_docs",
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
        self, query: str, k: int = 10
    ) -> list[dict]:
        query_embedding = self.llm_service.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
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
                "score": 1 - results["distances"][0][i],  # cosine -> similarity
            })
        return items

    def delete_by_document(self, document_id: int):
        self.collection.delete(where={"document_id": str(document_id)})

    def delete_by_ids(self, ids: list[str]):
        self.collection.delete(ids=ids)
