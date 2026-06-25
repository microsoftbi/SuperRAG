# backend/app/services/runtime_config.py
"""Runtime configuration persistence for RAG parameters."""

import json
from pathlib import Path

from app.config import settings

CONFIG_FILE = Path(settings.upload_dir).parent / "runtime_config.json"

DEFAULT_CONFIG = {
    "retriever_top_k": settings.retriever_top_k,
    "reranker_top_k": settings.reranker_top_k,
    "bm25_top_k": settings.bm25_top_k,
    "hybrid_fusion_k": settings.hybrid_fusion_k,
    "enable_query_rewriting": True,
    "enable_hybrid_retrieval": True,
    "enable_reranker": True,
    "chunk_size": settings.chunk_size,
    "chunk_overlap": settings.chunk_overlap,
    "llm_temperature": 0.7,
    "kg_max_depth": 5,
    "nl2sql_detail_logging": False,
    "nl2sql_max_rows": 50,
}


def load_runtime_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_runtime_config(updates: dict) -> dict:
    current = load_runtime_config()
    current.update(updates)
    CONFIG_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current
