# backend/app/api/knowledge_graph.py
"""Knowledge Graph management API.

全局知识图谱，不绑定知识库。
实体搜索和详情对所有登录用户开放，编辑操作仅限管理员。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.chunk import Chunk
from app.models.user import User
from app.models.kg_type import NodeType, RelationshipType
from app.services.auth_service import require_admin, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])

# ── 由 main.py 在启动时注入 ──
_neo4j_service = None
_entity_extractor = None
_doc_processor = None


def init_kg_routes(neo4j_service, entity_extractor, doc_processor):
    global _neo4j_service, _entity_extractor, _doc_processor
    _neo4j_service = neo4j_service
    _entity_extractor = entity_extractor
    _doc_processor = doc_processor


# ── Pydantic schemas ──

class EntityCreate(BaseModel):
    name: str
    type: str = "concept"
    properties: dict = {}


class EntityUpdate(BaseModel):
    name: str
    type: str
    properties: dict = {}


class RelationshipCreate(BaseModel):
    source: str
    target: str
    type: str


class RelationshipDelete(BaseModel):
    source: str
    target: str
    type: str


class RelationshipUpdate(BaseModel):
    source: str
    target: str
    old_type: str
    new_type: str


# ── 类型管理 Pydantic schemas ──

class NodeTypeCreate(BaseModel):
    name: str
    label: str
    color: str = "#607d8b"
    description: str = ""


class NodeTypeUpdate(BaseModel):
    label: str
    color: str = "#607d8b"
    description: str = ""


class RelTypeCreate(BaseModel):
    name: str
    label: str
    color: str = "#5e35b1"
    description: str = ""


class RelTypeUpdate(BaseModel):
    label: str
    color: str = "#5e35b1"
    description: str = ""


# ── 类型校验辅助函数 ──

def _validate_node_type(db: Session, type_name: str | None):
    """校验节点类型是否已注册，未注册则报 422。"""
    if not type_name or not type_name.strip():
        raise HTTPException(status_code=422, detail="节点类型不能为空")
    exists = db.query(NodeType).filter(NodeType.name == type_name.strip()).first()
    if not exists:
        raise HTTPException(
            status_code=422,
            detail=f"节点类型 '{type_name}' 未注册。请先在「类型管理」中创建该类型。",
        )


def _validate_rel_type(db: Session, type_name: str | None):
    """校验关系类型是否已注册。"""
    if not type_name or not type_name.strip():
        raise HTTPException(status_code=422, detail="关系类型不能为空")
    exists = db.query(RelationshipType).filter(RelationshipType.name == type_name.strip()).first()
    if not exists:
        raise HTTPException(
            status_code=422,
            detail=f"关系类型 '{type_name}' 未注册。请先在「类型管理」中创建该类型。",
        )


# ── 类型管理端点 ──

@router.get("/node-types")
def list_node_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """列出所有已注册的节点类型（含颜色/标签/描述）。"""
    return db.query(NodeType).order_by(NodeType.name).all()


@router.post("/node-types")
def create_node_type(
    data: NodeTypeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """创建节点类型。"""
    existing = db.query(NodeType).filter(NodeType.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"节点类型 '{data.name}' 已存在")
    nt = NodeType(name=data.name, label=data.label, color=data.color, description=data.description)
    db.add(nt)
    db.commit()
    return {"message": "created", "name": data.name}


@router.put("/node-types/{name}")
def update_node_type(
    name: str,
    data: NodeTypeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """更新节点类型的显示名/颜色/描述。"""
    nt = db.query(NodeType).filter(NodeType.name == name).first()
    if not nt:
        raise HTTPException(status_code=404, detail=f"节点类型 '{name}' 不存在")
    nt.label = data.label
    nt.color = data.color
    nt.description = data.description
    db.commit()
    return {"message": "updated"}


@router.delete("/node-types/{name}")
def delete_node_type(
    name: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """删除节点类型（如果被 Neo4j 中的节点使用则拒绝）。"""
    nt = db.query(NodeType).filter(NodeType.name == name).first()
    if not nt:
        raise HTTPException(status_code=404, detail=f"节点类型 '{name}' 不存在")
    # 检查 Neo4j 中是否已被使用
    if _neo4j_service:
        used = _neo4j_service.count_entities_by_type(name)
        if used > 0:
            raise HTTPException(
                status_code=409,
                detail=f"节点类型 '{name}' 已被 {used} 个节点使用，不能删除。请先修改这些节点的类型。",
            )
    db.delete(nt)
    db.commit()
    return {"message": "deleted"}


@router.get("/relation-types")
def list_relation_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """列出所有已注册的关系类型。"""
    return db.query(RelationshipType).order_by(RelationshipType.name).all()


@router.post("/relation-types")
def create_relation_type(
    data: RelTypeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """创建关系类型。"""
    existing = db.query(RelationshipType).filter(RelationshipType.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"关系类型 '{data.name}' 已存在")
    rt = RelationshipType(name=data.name, label=data.label, color=data.color, description=data.description)
    db.add(rt)
    db.commit()
    return {"message": "created", "name": data.name}


@router.put("/relation-types/{name}")
def update_relation_type(
    name: str,
    data: RelTypeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """更新关系类型。"""
    rt = db.query(RelationshipType).filter(RelationshipType.name == name).first()
    if not rt:
        raise HTTPException(status_code=404, detail=f"关系类型 '{name}' 不存在")
    rt.label = data.label
    rt.color = data.color
    rt.description = data.description
    db.commit()
    return {"message": "updated"}


@router.delete("/relation-types/{name}")
def delete_relation_type(
    name: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """删除关系类型。"""
    rt = db.query(RelationshipType).filter(RelationshipType.name == name).first()
    if not rt:
        raise HTTPException(status_code=404, detail=f"关系类型 '{name}' 不存在")
    # 检查 Neo4j 中是否已被使用（查询边的关系类型）
    if _neo4j_service:
        used = _neo4j_service.count_relationships_by_type(name)
        if used > 0:
            raise HTTPException(
                status_code=409,
                detail=f"关系类型 '{name}' 已被 {used} 条关系使用，不能删除。",
            )
    db.delete(rt)
    db.commit()
    return {"message": "deleted"}


# ── 路由 ──

@router.get("/entity-types")
def get_entity_types(user: User = Depends(get_current_user)):
    """获取知识图谱中所有已使用的实体类型。"""
    if not _neo4j_service:
        return []
    try:
        return _neo4j_service.get_distinct_types()
    except Exception as e:
        logger.error("get_entity_types failed: %s", e)
        return []


@router.get("/graph")
def get_graph(user: User = Depends(get_current_user)):
    """获取全局图谱（前端可视化用）。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        return _neo4j_service.get_full_graph()
    except Exception as e:
        logger.error("Failed to get graph: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/search")
def search_entities(
    q: str,
    user: User = Depends(get_current_user),
):
    """模糊搜索实体。"""
    if not _neo4j_service:
        return []
    try:
        return _neo4j_service.search_entities(q)
    except Exception as e:
        logger.error("Entity search failed: %s", e)
        return []


@router.get("/entities/{entity_id}")
def get_entity_detail(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """实体详情：基本信息 + 关联 chunk 预览。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        entities = _neo4j_service.search_entities("", limit=1000)
        entity = next((e for e in entities if e.get("id") == entity_id), None)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        chunk_ids = entity.get("chunk_ids") or []
        chunks = []
        if chunk_ids:
            stmt = select(Chunk).where(Chunk.id.in_(chunk_ids)).limit(20)
            for chunk in db.execute(stmt).scalars():
                chunks.append({
                    "id": chunk.id,
                    "content": chunk.content[:300],
                    "document_id": chunk.document_id,
                })

        return {"entity": entity, "chunks": chunks}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Entity detail failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract")
def rebuild_graph(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """重建全局图谱（重跑所有 ready 文档的实体提取）。"""
    if not _neo4j_service or not _entity_extractor or not _doc_processor:
        raise HTTPException(status_code=503, detail="KG services not initialized")

    from app.models.document import Document, DocumentStatus
    from app.models.chunk import Chunk
    from sqlalchemy import select

    _neo4j_service.delete_all_graph()

    total_entities = 0
    total_relations = 0
    processed = 0
    failed = 0

    docs = db.query(Document).filter(Document.status == DocumentStatus.READY.value).all()
    for doc in docs:
        try:
            text = _doc_processor.extract_text(doc.file_path)
            if not text.strip():
                processed += 1
                continue

            # 确保全文存了 SQLite（1条，不分块）
            existing_chunks = db.execute(
                select(Chunk).where(Chunk.document_id == doc.id).limit(1)
            ).first()
            if not existing_chunks:
                chunk = Chunk(
                    document_id=doc.id,
                    content=text,
                    chunk_index=0,
                    metadata_json=json.dumps({"source": "kg_full_text"}),
                )
                db.add(chunk)
                db.commit()

            chunk_ids = [c.id for c in doc.chunks]

            result = _entity_extractor.extract(text)
            if result["entities"]:
                _neo4j_service.import_extraction(
                    chunk_ids=chunk_ids,
                    entities=result["entities"],
                    relationships=result["relationships"],
                )
                total_entities += len(result["entities"])
                total_relations += len(result["relationships"])
            processed += 1
        except Exception as e:
            logger.error("Failed to extract entities for doc %d: %s", doc.id, e)
            failed += 1

    return {
        "message": "图谱重建完成",
        "entities": total_entities,
        "relationships": total_relations,
        "documents_processed": processed,
        "documents_failed": failed,
    }


@router.post("/entities")
def create_entity(
    data: EntityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """手动创建实体。校验类型是否已注册。"""
    _validate_node_type(db, data.type)
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    _neo4j_service.import_extraction(
        chunk_ids=[],
        entities=[{"name": data.name, "type": data.type, "properties": data.properties}],
        relationships=[],
    )
    return {"message": "created"}


@router.post("/relationships")
def create_relationship(
    data: RelationshipCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """手动创建关系。校验关系类型是否已注册。"""
    _validate_rel_type(db, data.type)
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    _neo4j_service.import_extraction(
        chunk_ids=[],
        entities=[],
        relationships=[{"source": data.source, "target": data.target, "type": data.type}],
    )
    return {"message": "created"}


@router.delete("/relationships")
def delete_relationship(
    data: RelationshipDelete,
    user: User = Depends(require_admin),
):
    """删除关系。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        _neo4j_service.delete_relationship(data.source, data.target, data.type)
        return {"message": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/batch-delete")
def batch_delete_relationships(
    data: dict,
    user: User = Depends(require_admin),
):
    """批量删除关系。"""
    rels = data.get("relationships", [])
    if not rels:
        raise HTTPException(status_code=400, detail="relationships is required")
    deleted = 0
    for rel in rels:
        try:
            _neo4j_service.delete_relationship(
                rel["source"], rel["target"], rel["type"],
            )
            deleted += 1
        except Exception as e:
            logger.warning("Failed to delete relationship: %s", e)
    return {"message": f"deleted {deleted}/{len(rels)}"}


@router.put("/relationships")
def update_relationship(
    data: RelationshipUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """修改关系类型（删旧+建新）。校验新关系类型。"""
    _validate_rel_type(db, data.new_type)
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        ok = _neo4j_service.update_relationship(
            data.source, data.target, data.old_type, data.new_type,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return {"message": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entities/{entity_id}")
def update_entity(
    entity_id: str,
    data: EntityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """修改节点（name / type / properties），保留所有关系。校验新类型。"""
    _validate_node_type(db, data.type)
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        result = _neo4j_service.update_entity(
            entity_id, data.name, data.type, data.properties,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        if result.get("conflict"):
            raise HTTPException(
                status_code=409,
                detail=f"名称 '{data.name}' 已被另一个节点使用",
            )
        return {"message": "updated", "id": entity_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entities/{entity_id}")
def delete_entity(
    entity_id: str,
    user: User = Depends(require_admin),
):
    """删除节点及其所有关系。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        ok = _neo4j_service.delete_entity(entity_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Entity not found")
        return {"message": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/batch-delete")
def batch_delete_entities(
    data: dict,
    user: User = Depends(require_admin),
):
    """批量删除节点（含级联关系）。"""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")
    deleted = 0
    for eid in ids:
        try:
            if _neo4j_service.delete_entity(eid):
                deleted += 1
        except Exception as e:
            logger.warning("Failed to delete entity %s: %s", eid, e)
    return {"message": f"deleted {deleted}/{len(ids)}"}


class CypherQuery(BaseModel):
    cypher: str


@router.get("/cypher-export")
def export_cypher(user: User = Depends(get_current_user)):
    """导出图谱为 Cypher CREATE 语句。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        _neo4j_service.export_cypher(),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=graph_export.cypher"},
    )


@router.post("/cypher")
def execute_cypher(
    data: CypherQuery,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """执行自定义 Cypher 查询（仅限管理员）。

    执行后会检查是否创建了未注册类型的节点/关系，并返回警告。
    """
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    result = _neo4j_service.execute_cypher(data.cypher)

    # 后检查：是否有未注册的类型被创建
    warnings = []
    if result.get("success"):
        try:
            # 检查节点类型
            unknown_node_types = _neo4j_service.find_unregistered_types(
                db, is_node=True
            )
            if unknown_node_types:
                warnings.append(
                    f"以下节点类型未在「类型管理」中注册，请前往注册以获得正确颜色: "
                    f"{', '.join(unknown_node_types)}"
                )
            # 检查关系类型
            unknown_rel_types = _neo4j_service.find_unregistered_types(
                db, is_node=False
            )
            if unknown_rel_types:
                warnings.append(
                    f"以下关系类型未在「类型管理」中注册，请前往注册以获得正确颜色: "
                    f"{', '.join(unknown_rel_types)}"
                )
        except Exception as e:
            logger.warning("Type check after Cypher execution failed: %s", e)

    if warnings:
        result["warnings"] = warnings
    return result


@router.get("/entities/{entity_id}/relationship-count")
def get_entity_rel_count(
    entity_id: str,
    user: User = Depends(get_current_user),
):
    """获取节点的关系数（用于删除前确认）。"""
    if not _neo4j_service:
        raise HTTPException(status_code=503, detail="Neo4j service not initialized")
    try:
        return {"count": _neo4j_service.count_entity_relationships(entity_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))