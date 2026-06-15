from app.services.vector_store import VectorStoreService


class Retriever:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        return self.vector_store.similarity_search(query, k=k)
