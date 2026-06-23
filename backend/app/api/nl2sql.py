# backend/app/api/nl2sql.py
"""NL2SQL 配置管理 API：连接配置 + 测试连接 + 提示词管理。"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.services.auth_service import require_admin
from app.services.nl2sql_config import load_nl2sql_config, save_nl2sql_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nl2sql", tags=["nl2sql"])


class TestConnectionRequest(BaseModel):
    host: str
    port: int = 1433
    username: str = ""
    password: str = ""
    database: str = ""


@router.get("/config")
def get_nl2sql_config(user: User = Depends(require_admin)):
    """获取 NL2SQL 配置（连接信息 + 提示词）。"""
    return load_nl2sql_config()


@router.put("/config")
def update_nl2sql_config(updates: dict, user: User = Depends(require_admin)):
    """保存 NL2SQL 配置。"""
    return save_nl2sql_config(updates)


@router.post("/test")
def test_connection(req: TestConnectionRequest, user: User = Depends(require_admin)):
    """测试 SQL Server 连接是否可用。"""
    try:
        import pyodbc

        # 通过 FreeTDS ODBC 驱动连接 SQL Server
        driver_paths = [
            "/opt/homebrew/Cellar/freetds/1.5.18/lib/libtdsodbc.so",
            "/usr/local/lib/libtdsodbc.so",
            "/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so",
        ]
        drv = None
        for p in driver_paths:
            import os
            if os.path.exists(p):
                drv = p
                break
        if not drv:
            return {"success": False, "message": "未找到 FreeTDS ODBC 驱动，请安装 freetds"}

        conn_str = (
            f"DRIVER={{{drv}}};"
            f"SERVER={req.host};PORT={req.port};"
            f"UID={req.username};PWD={req.password};"
            f"DATABASE={req.database};CHARSET=UTF8;"
        )
        conn = pyodbc.connect(conn_str, timeout=5, autocommit=True)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"success": True, "message": "连接成功"}
    except ImportError:
        raise HTTPException(status_code=500, detail="pyodbc 未安装")
    except Exception as e:
        return {"success": False, "message": str(e)}