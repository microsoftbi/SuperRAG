# backend/app/api/config.py
from fastapi import APIRouter, Depends

from app.config import settings
from app.models.user import User
from app.services.auth_service import require_admin
from app.services.runtime_config import load_runtime_config, save_runtime_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(user: User = Depends(require_admin)):
    config = load_runtime_config()
    config["app_version"] = settings.app_version
    return config


@router.put("")
def update_config(updates: dict, user: User = Depends(require_admin)):
    return save_runtime_config(updates)