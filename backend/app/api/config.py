# backend/app/api/config.py
from fastapi import APIRouter, Depends

from app.models.user import User
from app.services.auth_service import require_admin
from app.services.runtime_config import load_runtime_config, save_runtime_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(user: User = Depends(require_admin)):
    return load_runtime_config()


@router.put("")
def update_config(updates: dict, user: User = Depends(require_admin)):
    return save_runtime_config(updates)
