from app.config import settings
from app.services.vector_store import VectorStoreService


class Retriever:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        top_k = k or settings.retriever_top_k
        results = self.vector_store.similarity_search(query, k=top_k)
        return results
