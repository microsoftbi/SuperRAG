# backend/tests/test_document_upload.py
"""Document upload → vector store (Milvus Lite) 的端到端测试。

策略：
- 使用 FastAPI TestClient 走完整 HTTP 路由
- Mock LLMService.embed() 返回全零向量（避免真实 API 调用）
- 上传的临时文件自动清理
- Milvus Lite 数据库在测试前后重建
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import settings
from app.models.document import DocumentStatus


# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_embed():
    """Mock LLMService.embed() to return zero vectors (avoids real API)."""
    with patch("app.services.llm_service.LLMService.embed") as mock:
        mock.return_value = [[0.0] * settings.embedding_dim]
        yield mock


@pytest.fixture
def txt_file():
    """Create a temporary .txt file for upload."""
    with tempfile.NamedTemporaryFile(
        suffix=".txt", mode="w", delete=False, encoding="utf-8",
    ) as f:
        f.write("数据中心建设方案包括服务器硬件配置和网络设备。\n")
        f.write("数据库集群部署在数据中心机房的服务器上。\n")
        f.write("网络架构设计与安全策略文档。\n")
        f.flush()
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def md_file():
    with tempfile.NamedTemporaryFile(
        suffix=".md", mode="w", delete=False, encoding="utf-8",
    ) as f:
        f.write("# 测试文档\n\n这是 **Markdown** 格式的测试内容。\n")
        f.flush()
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture(autouse=True)
def clean_upload_dir():
    """清理 uploads 目录。"""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    for f in upload_dir.iterdir():
        f.unlink()


# ─────────────────────────────────────────────────────────
# 文档上传测试
# ─────────────────────────────────────────────────────────


class TestDocumentUpload:
    """测试文档上传到向量数据库的完整流程。"""

    def test_upload_txt_success(self, test_client, admin_token, txt_file):
        """上传 .txt 文件，验证返回就绪状态。"""
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={
                    "title": "数据中心方案",
                    "category": "tech",
                    "store": "vector",
                    "knowledge_base_ids": "[]",
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "数据中心方案"
        assert data["status"] == DocumentStatus.READY.value
        assert data["doc_type"] == "txt"
        assert data["store"] == "vector"
        assert data["id"] > 0
        assert "created_at" in data

    def test_upload_without_title_uses_filename(self, test_client, admin_token, txt_file):
        """不传 title 时应该用文件名代替。"""
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("数据中心方案.txt", f, "text/plain")},
                data={"store": "vector", "knowledge_base_ids": "[]"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert response.status_code == 200
        assert response.json()["title"] == "数据中心方案"

    def test_upload_unsupported_file_type(self, test_client, admin_token):
        """不支持的扩展名 → 400。"""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.exe", b"fake", "application/x-msdownload")},
            data={"store": "vector", "knowledge_base_ids": "[]"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]

    def test_upload_without_filename(self, test_client, admin_token):
        """无文件名 → 422（Pydantic 校验拒绝）。"""
        response = test_client.post(
            "/api/v1/documents/upload",
            files={"file": ("", b"data", "text/plain")},
            data={"store": "vector", "knowledge_base_ids": "[]"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_upload_invalid_store(self, test_client, admin_token, txt_file):
        """非法的 store 值 → 400。"""
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"store": "invalid", "knowledge_base_ids": "[]"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert response.status_code == 400
        assert "Invalid store" in response.json()["detail"]

    def test_upload_no_auth(self, test_client, txt_file):
        """未认证 → 401。"""
        with open(txt_file, "rb") as f:
            response = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"store": "vector", "knowledge_base_ids": "[]"},
            )
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────
# 文档列表/查询测试
# ─────────────────────────────────────────────────────────


class TestDocumentList:
    """文档列表查询。"""

    def _upload(self, test_client, admin_token, content, title="doc"):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()
            with open(f.name, "rb") as f2:
                resp = test_client.post(
                    "/api/v1/documents/upload",
                    files={"file": (f"{title}.txt", f2, "text/plain")},
                    data={"title": title, "store": "vector", "knowledge_base_ids": "[]"},
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            os.unlink(f.name)
            return resp.json()

    def test_list_documents(self, test_client, admin_token):
        """上传文档后列表应包含它。"""
        doc = self._upload(test_client, admin_token, "测试内容", "测试文档A")
        doc_id = doc["id"]

        resp = test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        ids = [d["id"] for d in data["items"]]
        assert doc_id in ids

    def test_list_documents_filter_status(self, test_client, admin_token):
        """按 status 过滤。"""
        doc = self._upload(test_client, admin_token, "内容", "状态测试")
        # ready 状态的过滤
        resp = test_client.get(
            "/api/v1/documents",
            params={"status": "ready"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc["id"] in ids

        # pending 状态的过滤（应无结果）
        resp = test_client.get(
            "/api/v1/documents",
            params={"status": "pending"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc["id"] not in ids

    def test_list_documents_filter_store(self, test_client, admin_token):
        """按 store 过滤。"""
        doc = self._upload(test_client, admin_token, "内容", "存储测试")
        resp = test_client.get(
            "/api/v1/documents",
            params={"store": "vector"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc["id"] in ids


# ─────────────────────────────────────────────────────────
# 文档分块查询测试
# ─────────────────────────────────────────────────────────


class TestDocumentChunks:
    """文档处理后，分块应在向量库中。"""

    def test_get_chunks_after_upload(self, test_client, admin_token, mock_embed):
        """上传文档后应能在 Milvus 中查到分块。"""
        content = "第一段内容。\n\n第二段内容。\n\n第三段内容。\n\n第四段内容。\n\n第五段内容。"
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()

            with open(f.name, "rb") as f2:
                resp = test_client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("chunks_test.txt", f2, "text/plain")},
                    data={"title": "分块测试", "store": "vector", "knowledge_base_ids": "[]"},
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            os.unlink(f.name)

        assert resp.status_code == 200
        doc_id = resp.json()["id"]

        # 查询分块
        resp = test_client.get(
            f"/api/v1/documents/{doc_id}/chunks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        chunks = resp.json()
        assert len(chunks["chunks"]) > 0
        # 分块应按 chunk_index 排序
        indices = [c["chunk_index"] for c in chunks["chunks"]]
        assert indices == sorted(indices)

    def test_get_chunks_not_found(self, test_client, admin_token):
        """不存在的文档 → 404。"""
        resp = test_client.get(
            "/api/v1/documents/99999/chunks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────
# 文档删除测试
# ─────────────────────────────────────────────────────────


class TestDocumentDelete:
    """删除文档后向量库也应同步清理。"""

    def test_delete_document(self, test_client, admin_token, mock_embed):
        """删除文档后不应在列表中。"""
        # 上传
        content = "待删除的文档内容。"
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()
            with open(f.name, "rb") as f2:
                resp = test_client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("delete_me.txt", f2, "text/plain")},
                    data={"title": "待删除", "store": "vector", "knowledge_base_ids": "[]"},
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            os.unlink(f.name)

        doc_id = resp.json()["id"]

        # 删除
        resp = test_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # 验证不在列表中
        resp = test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc_id not in ids

        # 分块查询应 404
        resp = test_client.get(
            f"/api/v1/documents/{doc_id}/chunks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_delete_not_found(self, test_client, admin_token):
        """删除不存在的文档 → 404。"""
        resp = test_client.delete(
            "/api/v1/documents/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────
# 文档重试测试
# ─────────────────────────────────────────────────────────


class TestDocumentReprocess:
    """重新处理失败文档。"""

    def test_reprocess_ready_document(self, test_client, admin_token, txt_file, mock_embed):
        """已就绪的文档也可以 reprocess。"""
        with open(txt_file, "rb") as f:
            resp = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("reprocess.txt", f, "text/plain")},
                data={"title": "重试测试", "store": "vector", "knowledge_base_ids": "[]"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        doc_id = resp.json()["id"]

        # reprocess
        resp = test_client.post(
            f"/api/v1/documents/{doc_id}/reprocess",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "reprocessed"

    def test_reprocess_not_found(self, test_client, admin_token):
        """不存在的文档 → 404。"""
        resp = test_client.post(
            "/api/v1/documents/99999/reprocess",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────
# 完整生命周期测试
# ─────────────────────────────────────────────────────────


class TestDocumentLifecycle:
    """文档的完整生命周期：上传 → 查看 → 重试 → 删除。"""

    def test_full_lifecycle(self, test_client, admin_token, mock_embed):
        """上传 → 列表确认 → 查看分块 → 重试 → 删除 全流程。"""
        content = "生命周期测试文档内容。\n这是第二行。"
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()
            with open(f.name, "rb") as f2:
                # 1. 上传
                resp = test_client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("lifecycle.txt", f2, "text/plain")},
                    data={"title": "生命周期", "store": "vector", "knowledge_base_ids": "[]"},
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            os.unlink(f.name)

        assert resp.status_code == 200
        doc_id = resp.json()["id"]
        assert resp.json()["status"] == DocumentStatus.READY.value

        # 2. 列表确认
        resp = test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc_id in ids

        # 3. 查看分块
        resp = test_client.get(
            f"/api/v1/documents/{doc_id}/chunks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["chunks"]) > 0

        # 4. 重试
        resp = test_client.post(
            f"/api/v1/documents/{doc_id}/reprocess",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # 5. 删除
        resp = test_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # 6. 验证已删除
        resp = test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        ids = [d["id"] for d in resp.json()["items"]]
        assert doc_id not in ids
