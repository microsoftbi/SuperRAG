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


# ── 路由 ──

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
    user: User = Depends(require_admin),
):
    """手动创建实体。"""
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
    user: User = Depends(require_admin),
):
    """手动创建关系。"""
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
    user: User = Depends(require_admin),
):
    """修改关系类型（删旧+建新）。"""
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
    user: User = Depends(require_admin),
):
    """修改节点（name / type / properties），保留所有关系。"""
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