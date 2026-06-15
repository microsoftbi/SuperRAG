from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    volc_access_key: str = ""
    volc_secret_key: str = ""
    volc_endpoint: str = "ark.cn-beijing.volces.com"
    llm_model_name: str = ""
    embedding_model_name: str = ""
    chroma_persist_dir: str = "./chroma_db"
    database_url: str = "sqlite:///./sprag.db"
    upload_dir: str = "./uploads"

    # RAG 参数
    chunk_size: int = 500
    chunk_overlap: int = 50
    retriever_top_k: int = 10
    reranker_top_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

# 确保目录存在
Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
