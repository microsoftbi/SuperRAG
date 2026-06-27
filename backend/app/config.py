import os
from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录 = backend/（config.py 在 backend/app/ 下，往上一级）
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_version: str = "0.2.0"
    volc_api_key: str = ""
    volc_endpoint: str = "ark.cn-beijing.volces.com"
    llm_model_name: str = ""
    embedding_model_name: str = ""
    embedding_dim: int = 2048
    milvus_lite_uri: str = str(BACKEND_DIR / "milvus_lite.db")
    database_url: str = f"sqlite:///{BACKEND_DIR / 'sprag.db'}"
    upload_dir: str = str(BACKEND_DIR / "uploads")

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

# 环境变量可以覆盖，未设置时用绝对路径
if not os.environ.get("DATABASE_URL"):
    settings.database_url = f"sqlite:///{BACKEND_DIR / 'sprag.db'}"
if not os.environ.get("MILVUS_LITE_URI"):
    settings.milvus_lite_uri = str(BACKEND_DIR / "milvus_lite.db")
if not os.environ.get("UPLOAD_DIR"):
    settings.upload_dir = str(BACKEND_DIR / "uploads")

# 确保 .env 从正确的路径加载
_env_path = BACKEND_DIR / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'\"")
        if not os.environ.get(key):
            os.environ[key] = val
    # 用环境变量覆盖重新创建 settings
    settings = Settings()


def ensure_dirs() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)