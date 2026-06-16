# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.knowledge_base import user_knowledge_base
from app.models.user import User
from app.schemas.knowledge_base import UserKnowledgeBaseUpdate
from app.schemas.user import UserResponse
from app.services.auth_service import require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).all()


@router.get("/{user_id}/knowledge-bases", response_model=list[int])
def get_user_knowledge_bases(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    rows = db.execute(
        user_knowledge_base.select().where(user_knowledge_base.c.user_id == user_id)
    ).all()
    return [row.knowledge_base_id for row in rows]


@router.put("/{user_id}/knowledge-bases")
def set_user_knowledge_bases(
    user_id: int,
    data: UserKnowledgeBaseUpdate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.execute(
        user_knowledge_base.delete().where(user_knowledge_base.c.user_id == user_id)
    )
    for kb_id in data.knowledge_base_ids:
        db.execute(
            user_knowledge_base.insert().values(
                user_id=user_id, knowledge_base_id=kb_id
            )
        )
    db.commit()
    return {"message": "ok"}