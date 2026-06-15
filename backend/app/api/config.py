# backend/app/api/config.py
from fastapi import APIRouter

from app.services.runtime_config import load_runtime_config, save_runtime_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config():
    return load_runtime_config()


@router.put("")
def update_config(updates: dict):
    current = save_runtime_config(updates)
    return current
