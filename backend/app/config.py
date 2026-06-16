from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    volc_api_key: str = ""
    volc_endpoint: str = "ark.cn-beijing.volces.com"
    llm_model_name: str = ""
    embedding_model_name: str = ""
    chroma_persist_dir: str = "./chroma_db"
    database_url: str = "sqlite:///./sprag.db"
    upload_dir: str = "./uploads"

    jwt_secret_key: str = "sprag-default-secret-change-in-production"
    jwt_auto_create_admin: bool = True
    default_admin_password: str = "admin123"

    chunk_size: int = 500
    chunk_overlap: int = 50
    retriever_top_k: int = 10
    reranker_top_k: int = 5

    # Phase 2: 检索增强
    enable_query_rewriting: bool = True
    enable_hybrid_retrieval: bool = True
    enable_reranker: bool = True
    bm25_top_k: int = 10
    hybrid_fusion_k: int = 60

    class Config:
        env_file = ".env"


settings = Settings()


def ensure_dirs() -> None:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
