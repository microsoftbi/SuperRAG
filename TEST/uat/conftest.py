"""Playwright fixtures for SPRAG UAT.

Each test gets its own fresh page with API mocking.
set_logged_in() helper sets localStorage then navigates to admin.
"""

import json
import pytest

BASE_URL = "http://localhost:5173"
MOCK_TOKEN = "test-token-12345"

MOCK_SESSIONS = {
    "sessions": [
        {"session_id": "s1", "first_query": "数据中心建设方案", "title": "", "last_active": "2026-06-25T10:00:00"},
    ]
}
MOCK_DOCUMENTS = {
    "total": 3,
    "items": [
        {"id": 1, "title": "数据中心方案", "doc_type": "txt", "status": "ready", "store": "vector",
         "knowledge_base_ids": [], "created_at": "2026-06-25T10:00:00"},
    ]
}
MOCK_CHUNKS = {"chunks": [{"chunk_id": "c1", "chunk_index": 0, "content": "数据中心建设方案包括服务器硬件配置和网络设备。", "metadata": {"document_title": "数据中心方案"}}]}
MOCK_GRAPH = {
    "nodes": [
        {"id": "n1", "name": "张三", "type": "person", "chunk_count": 3, "properties": "{}", "labels": ["Entity"]},
        {"id": "n2", "name": "公司A", "type": "org", "chunk_count": 5, "properties": "{}", "labels": ["Entity"]},
    ],
    "edges": [{"source": "n1", "target": "n2", "type": "任职于"}],
}
MOCK_CONFIG = {
    "retriever_top_k": 10, "reranker_top_k": 5, "bm25_top_k": 10,
    "hybrid_fusion_k": 60, "enable_hybrid_retrieval": True,
    "enable_reranker": True, "llm_temperature": 0.7,
    "nl2sql_detail_logging": False, "nl2sql_max_rows": 50,
}
MOCK_DOC_UPLOAD_OK = {"id": 99, "title": "测试文档", "doc_type": "txt", "status": "ready", "store": "vector", "knowledge_base_ids": [], "created_at": "2026-06-25T12:00:00"}
MOCK_LOGIN_OK = {"access_token": MOCK_TOKEN, "user": {"id": 1, "username": "admin", "role": "admin"}}
MOCK_LOGIN_FAIL = {"detail": "用户名或密码错误"}


def _handle_route(route):
    url = route.request.url
    method = route.request.method
    def _json(data, status=200):
        route.fulfill(status=status, content_type="application/json",
                       body=json.dumps(data, ensure_ascii=False))
    if url.endswith("/api/v1/auth/login") and method == "POST":
        body = json.loads(route.request.post_data or "{}")
        _json(MOCK_LOGIN_OK if body.get("password") == "admin123" else MOCK_LOGIN_FAIL,
              200 if body.get("password") == "admin123" else 401)
        return
    if url.endswith("/api/v1/chat/sessions") and method == "GET": _json(MOCK_SESSIONS); return
    if "/api/v1/chat/sessions/" in url and method == "DELETE": _json({"message": "deleted"}); return
    if "/api/v1/chat/sessions/" in url and method == "PUT": _json({"message": "renamed"}); return
    if url.endswith("/api/v1/documents") and method == "GET": _json(MOCK_DOCUMENTS); return
    if url.endswith("/api/v1/documents/upload") and method == "POST": _json(MOCK_DOC_UPLOAD_OK); return
    if "/api/v1/documents/" in url and url.endswith("/chunks") and method == "GET": _json(MOCK_CHUNKS); return
    if "/api/v1/documents/" in url and method == "DELETE": _json({"message": "deleted"}); return
    if url.endswith("/api/v1/knowledge-graph/graph") and method == "GET": _json(MOCK_GRAPH); return
    if url.endswith("/api/v1/config") and method == "GET": _json(MOCK_CONFIG); return
    if url.endswith("/api/v1/config") and method == "PUT": _json({**MOCK_CONFIG, "nl2sql_max_rows": 200}); return
    if url.endswith("/health"): _json({"status": "ok"}); return
    route.continue_()


@pytest.fixture
def page(page):
    """Inject API mocks into every page."""
    page.route("**/api/**", _handle_route)
    yield page


def do_login(page):
    """Fill login form and return page at admin panel."""
    page.goto(f"{BASE_URL}/login")
    page.wait_for_selector("input[placeholder*='用户名']")
    page.fill("input[placeholder*='用户名']", "admin")
    page.fill("input[placeholder*='密码']", "admin123")
    with page.expect_navigation():
        page.click("button:has-text('登录')")
    page.wait_for_url("**/admin*")
