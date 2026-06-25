from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    volc_api_key: str = ""
    volc_endpoint: str = "ark.cn-beijing.volces.com"
    llm_model_name: str = ""
    embedding_model_name: str = ""
    embedding_dim: int = 2048
    milvus_lite_uri: str = "./milvus_lite.db"
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

    # Neo4j 知识图谱
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j"

    # KG 功能开关
    enable_knowledge_graph: bool = True
    kg_extract_on_upload: bool = True

    class Config:
        env_file = ".env"


settings = Settings()


def ensure_dirs() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
