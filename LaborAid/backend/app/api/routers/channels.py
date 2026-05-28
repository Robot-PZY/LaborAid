"""专项维权通道配置（与前端 special-channels.json 同源）"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.config import PROJECT_ROOT
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

_CONFIG_CANDIDATES = [
    PROJECT_ROOT / "frontend" / "src" / "config" / "labor" / "special-channels.json",
    PROJECT_ROOT / "config" / "labor" / "special-channels.json",
]


def _load_config() -> dict:
    for path in _CONFIG_CANDIDATES:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load special-channels from %s: %s", path, exc)
    return {"channels": {}, "report_links": {"default": {}, "by_province": {}}}


@router.get("")
async def get_channels(_: User = Depends(get_current_user)):
    return _load_config()


@router.get("/report-link")
async def get_report_link(
    province: str = Query(..., min_length=1),
    _: User = Depends(get_current_user),
):
    cfg = _load_config()
    links = cfg.get("report_links") or {}
    by_prov = links.get("by_province") or {}
    entry = by_prov.get(province.strip()) or links.get("default") or {}
    return entry
