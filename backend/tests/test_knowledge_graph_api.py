# backend/tests/test_knowledge_graph_api.py
"""KG 节点 / 关系维护 API 的集成测试。

策略：mock `app.api.knowledge_graph._neo4j_service` 为一个 FakeNeo4j，
绕开真实 Neo4j 数据库，验证 endpoint → service 的契约和错误处理。
"""

import pytest
from unittest.mock import MagicMock
from app.api import knowledge_graph as kg_api
from app.services.auth_service import require_admin, get_current_user
from app.main import app


# ─────────────────────────────────────────────────────────
# FakeNeo4jService — 仿真 in-memory 图存储
# ─────────────────────────────────────────────────────────


class FakeNeo4jService:
    """In-memory 仿真 Neo4j，行为对齐真实 service 的接口。"""

    def __init__(self):
        # entities: {id -> {name, type, properties, chunk_ids}}
        self.entities = {}
        # rels: list of (src_name, dst_name, type)
        self.rels = []
        self._id_counter = 0

    # === 写入 ===
    def import_extraction(self, chunk_ids, entities, relationships):
        for ent in entities:
            self._id_counter += 1
            eid = f"fake-{self._id_counter}"
            # 已存在同名 → 合并
            existing = next((k for k, v in self.entities.items() if v["name"] == ent["name"]), None)
            if existing:
                self.entities[existing]["type"] = ent.get("type", self.entities[existing]["type"])
            else:
                self.entities[eid] = {
                    "name": ent["name"],
                    "type": ent.get("type", "concept"),
                    "properties": ent.get("properties", {}),
                    "chunk_ids": list(chunk_ids),
                }
        for rel in relationships:
            self.rels.append((rel["source"], rel["target"], rel["type"]))

    # === 节点维护 ===
    def find_entity_by_id(self, internal_id):
        e = self.entities.get(internal_id)
        if not e:
            return None
        return {"id": internal_id, **e, "labels": ["Entity"]}

    def count_entity_relationships(self, internal_id):
        e = self.entities.get(internal_id)
        if not e:
            return 0
        name = e["name"]
        return sum(1 for s, t, _ in self.rels if s == name or t == name)

    def update_entity(self, internal_id, name, type, properties):
        e = self.entities.get(internal_id)
        if not e:
            return None
        # 改名冲突
        if name != e["name"]:
            conflict = next(
                (k for k, v in self.entities.items()
                 if v["name"] == name and k != internal_id),
                None,
            )
            if conflict:
                return {"conflict": True, "other_id": conflict}
        # 改名时同步更新 rels 里的引用
        if name != e["name"]:
            self.rels = [
                (name if s == e["name"] else s,
                 name if t == e["name"] else t,
                 rt)
                for s, t, rt in self.rels
            ]
        e["name"] = name
        e["type"] = type
        e["properties"] = properties
        return {"conflict": False, "id": internal_id, "name": name, "type": type}

    def delete_entity(self, internal_id):
        e = self.entities.pop(internal_id, None)
        if not e:
            return False
        name = e["name"]
        self.rels = [r for r in self.rels if r[0] != name and r[1] != name]
        return True

    def update_relationship(self, source_name, target_name, old_type, new_type):
        for i, (s, t, rt) in enumerate(self.rels):
            if s == source_name and t == target_name and rt == old_type:
                self.rels[i] = (s, t, new_type)
                return True
        return False

    def delete_relationship(self, source_name, target_name, rel_type):
        before = len(self.rels)
        self.rels = [r for r in self.rels
                     if not (r[0] == source_name and r[1] == target_name and r[2] == rel_type)]
        return len(self.rels) < before


# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────


@pytest.fixture
def fake_neo4j(monkeypatch):
    """注入 FakeNeo4jService 到 knowledge_graph 模块。"""
    fake = FakeNeo4jService()
    # 预置 2 个实体 + 1 条关系
    fake.entities = {
        "id-zhangsan": {"name": "张三", "type": "person", "properties": {}, "chunk_ids": []},
        "id-companyA": {"name": "公司A", "type": "org", "properties": {}, "chunk_ids": []},
    }
    fake.rels = [("张三", "公司A", "任职于")]
    monkeypatch.setattr(kg_api, "_neo4j_service", fake)
    return fake


@pytest.fixture
def admin_override():
    """绕开 admin 权限校验。"""
    fake_admin = MagicMock()
    fake_admin.id = 1
    fake_admin.role = "admin"
    app.dependency_overrides[require_admin] = lambda: fake_admin
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    yield
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client(admin_override):
    from fastapi.testclient import TestClient
    return TestClient(app)


# ─────────────────────────────────────────────────────────
# 节点维护
# ─────────────────────────────────────────────────────────


def test_create_entity(fake_neo4j, client):
    r = client.post("/api/v1/knowledge-graph/entities", json={
        "name": "李四", "type": "person", "properties": {"role": "工程师"},
    })
    assert r.status_code == 200
    assert any(e["name"] == "李四" for e in fake_neo4j.entities.values())


def test_update_entity_rename_ok(fake_neo4j, client):
    """重命名应保留 internal_id 并更新所有引用。"""
    r = client.put("/api/v1/knowledge-graph/entities/id-zhangsan", json={
        "name": "张三丰", "type": "person", "properties": {},
    })
    assert r.status_code == 200
    assert fake_neo4j.entities["id-zhangsan"]["name"] == "张三丰"
    # 关系里的源名也应该被更新
    assert any(s == "张三丰" for s, _, _ in fake_neo4j.rels)


def test_update_entity_rename_conflict(fake_neo4j, client):
    """改名为已存在的名字 → 409。"""
    r = client.put("/api/v1/knowledge-graph/entities/id-zhangsan", json={
        "name": "公司A", "type": "person", "properties": {},
    })
    assert r.status_code == 409
    assert "已被" in r.json()["detail"]


def test_update_entity_type_only(fake_neo4j, client):
    """只改类型(自定义类型也允许)。"""
    r = client.put("/api/v1/knowledge-graph/entities/id-zhangsan", json={
        "name": "张三", "type": "客户", "properties": {},  # 自定义类型
    })
    assert r.status_code == 200
    assert fake_neo4j.entities["id-zhangsan"]["type"] == "客户"


def test_update_entity_not_found(fake_neo4j, client):
    r = client.put("/api/v1/knowledge-graph/entities/nonexistent", json={
        "name": "x", "type": "person", "properties": {},
    })
    assert r.status_code == 404


def test_delete_entity_cascade(fake_neo4j, client):
    """删除节点应级联删边。"""
    assert any(s == "张三" for s, _, _ in fake_neo4j.rels)
    r = client.delete("/api/v1/knowledge-graph/entities/id-zhangsan")
    assert r.status_code == 200
    assert "id-zhangsan" not in fake_neo4j.entities
    # 关系应被级联删除
    assert not any(s == "张三" or t == "张三" for s, t, _ in fake_neo4j.rels)


def test_delete_entity_not_found(fake_neo4j, client):
    r = client.delete("/api/v1/knowledge-graph/entities/nonexistent")
    assert r.status_code == 404


def test_relationship_count(fake_neo4j, client):
    """删除前预查关系数。"""
    r = client.get("/api/v1/knowledge-graph/entities/id-zhangsan/relationship-count")
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r2 = client.get("/api/v1/knowledge-graph/entities/id-companyA/relationship-count")
    assert r2.json()["count"] == 1


# ─────────────────────────────────────────────────────────
# 关系维护
# ─────────────────────────────────────────────────────────


def test_create_relationship(fake_neo4j, client):
    r = client.post("/api/v1/knowledge-graph/relationships", json={
        "source": "张三", "target": "公司A", "type": "投资了",
    })
    assert r.status_code == 200
    assert ("张三", "公司A", "投资了") in fake_neo4j.rels


def test_update_relationship_ok(fake_neo4j, client):
    r = client.put("/api/v1/knowledge-graph/relationships", json={
        "source": "张三", "target": "公司A",
        "old_type": "任职于", "new_type": "创立了",
    })
    assert r.status_code == 200
    assert ("张三", "公司A", "创立了") in fake_neo4j.rels
    assert ("张三", "公司A", "任职于") not in fake_neo4j.rels


def test_update_relationship_not_found(fake_neo4j, client):
    r = client.put("/api/v1/knowledge-graph/relationships", json={
        "source": "张三", "target": "公司A",
        "old_type": "不存在的关系", "new_type": "别的",
    })
    assert r.status_code == 404


def test_delete_relationship(fake_neo4j, client):
    r = client.request("DELETE", "/api/v1/knowledge-graph/relationships", json={
        "source": "张三", "target": "公司A", "type": "任职于",
    })
    assert r.status_code == 200
    assert ("张三", "公司A", "任职于") not in fake_neo4j.rels


# ─────────────────────────────────────────────────────────
# 错误场景 & 边界
# ─────────────────────────────────────────────────────────


def test_neo4j_unavailable(monkeypatch, client):
    """Neo4j 未注入时所有写接口应返回 503。"""
    monkeypatch.setattr(kg_api, "_neo4j_service", None)

    r1 = client.put("/api/v1/knowledge-graph/entities/x", json={
        "name": "x", "type": "person", "properties": {},
    })
    assert r1.status_code == 503

    r2 = client.delete("/api/v1/knowledge-graph/entities/x")
    assert r2.status_code == 503

    r3 = client.put("/api/v1/knowledge-graph/relationships", json={
        "source": "a", "target": "b", "old_type": "x", "new_type": "y",
    })
    assert r3.status_code == 503


def test_update_entity_validation(fake_neo4j, client):
    """缺少必填字段 → 422。"""
    r = client.put("/api/v1/knowledge-graph/entities/id-zhangsan", json={
        # 缺 name 和 type
        "properties": {},
    })
    assert r.status_code == 422


def test_full_node_lifecycle(fake_neo4j, client):
    """新建 → 改名 → 加关系 → 改关系类型 → 删除节点（级联） 的完整流程。"""
    # 1. 新建
    r = client.post("/api/v1/knowledge-graph/entities", json={
        "name": "测试节点", "type": "concept", "properties": {},
    })
    assert r.status_code == 200
    new_id = next(k for k, v in fake_neo4j.entities.items() if v["name"] == "测试节点")

    # 2. 改名
    r = client.put(f"/api/v1/knowledge-graph/entities/{new_id}", json={
        "name": "改名后", "type": "concept", "properties": {"desc": "ok"},
    })
    assert r.status_code == 200
    assert fake_neo4j.entities[new_id]["name"] == "改名后"
    assert fake_neo4j.entities[new_id]["properties"] == {"desc": "ok"}

    # 3. 加关系
    r = client.post("/api/v1/knowledge-graph/relationships", json={
        "source": "改名后", "target": "公司A", "type": "属于",
    })
    assert r.status_code == 200

    # 4. 关系数 = 1
    r = client.get(f"/api/v1/knowledge-graph/entities/{new_id}/relationship-count")
    assert r.json()["count"] == 1

    # 5. 改关系类型
    r = client.put("/api/v1/knowledge-graph/relationships", json={
        "source": "改名后", "target": "公司A",
        "old_type": "属于", "new_type": "隶属于",
    })
    assert r.status_code == 200
    assert ("改名后", "公司A", "隶属于") in fake_neo4j.rels

    # 6. 删除节点 → 级联
    r = client.delete(f"/api/v1/knowledge-graph/entities/{new_id}")
    assert r.status_code == 200
    assert new_id not in fake_neo4j.entities
    assert not any(s == "改名后" or t == "改名后" for s, t, _ in fake_neo4j.rels)
