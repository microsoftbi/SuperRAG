# backend/app/api/knowledge_bases.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.knowledge_base import KnowledgeBase, document_knowledge_base
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse
from app.services.auth_service import get_current_user, require_admin

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.get("", response_model=list[KnowledgeBaseResponse])
def list_knowledge_bases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "admin":
        kbs = db.query(KnowledgeBase).all()
    else:
        kbs = (
            db.query(KnowledgeBase)
            .join("user_knowledge_base")
            .filter(user_knowledge_base.c.user_id == user.id)
            .all()
        )

    results = []
    for kb in kbs:
        doc_count = db.query(document_knowledge_base).filter(
            document_knowledge_base.c.knowledge_base_id == kb.id
        ).count()
        results.append(KnowledgeBaseResponse(
            id=kb.id, name=kb.name, description=kb.description,
            doc_count=doc_count,
            created_at=kb.created_at, updated_at=kb.updated_at,
        ))
    return results


@router.post("", response_model=KnowledgeBaseResponse)
def create_knowledge_base(
    data: KnowledgeBaseCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="知识库名称已存在")
    kb = KnowledgeBase(name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return KnowledgeBaseResponse(
        id=kb.id, name=kb.name, description=kb.description,
        doc_count=0, created_at=kb.created_at, updated_at=kb.updated_at,
    )


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    kb_id: int,
    data: KnowledgeBaseCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    kb.name = data.name
    kb.description = data.description
    db.commit()
    db.refresh(kb)
    doc_count = db.query(document_knowledge_base).filter(
        document_knowledge_base.c.knowledge_base_id == kb.id
    ).count()
    return KnowledgeBaseResponse(
        id=kb.id, name=kb.name, description=kb.description,
        doc_count=doc_count,
        created_at=kb.created_at, updated_at=kb.updated_at,
    )


@router.get("/{kb_id}/documents", response_model=list[int])
def get_kb_documents(
    kb_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all document IDs in this knowledge base."""
    rows = db.execute(
        document_knowledge_base.select().where(
            document_knowledge_base.c.knowledge_base_id == kb_id
        )
    ).all()
    return [row.document_id for row in rows]


@router.put("/{kb_id}/documents")
def set_kb_documents(
    kb_id: int,
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Set which documents belong to this knowledge base."""
    doc_ids = data.get("document_ids", [])
    # Remove all current docs from this KB
    db.execute(
        document_knowledge_base.delete().where(
            document_knowledge_base.c.knowledge_base_id == kb_id
        )
    )
    # Add new docs
    for doc_id in doc_ids:
        db.execute(
            document_knowledge_base.insert().values(
                document_id=doc_id, knowledge_base_id=kb_id
            )
        )
    db.commit()
    return {"message": "ok"}


@router.delete("/{kb_id}")
def delete_knowledge_base(
    kb_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    db.execute(
        document_knowledge_base.delete().where(
            document_knowledge_base.c.knowledge_base_id == kb_id
        )
    )
    db.delete(kb)
    db.commit()
    return {"message": "deleted"}