# backend/app/services/nl2sql_config.py
"""NL2SQL 配置持久化（独立 JSON 文件）。"""

import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(settings.upload_dir).parent / "nl2sql_config.json"

DEFAULT_CONFIG = {
    "connection": {
        "conn_name": "",
        "host": "",
        "port": 1433,
        "username": "",
        "password": "",
        "database": "",
    },
    "prompts": {
        "schema": "",
        "terms": "",
        "qa_pairs": "",
    },
}


def load_nl2sql_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load nl2sql config: %s", e)
    return dict(DEFAULT_CONFIG)


def save_nl2sql_config(updates: dict) -> dict:
    current = load_nl2sql_config()
    current.update(updates)
    CONFIG_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current