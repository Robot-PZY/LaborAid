"""维权指引与官方服务链接（登录用户可读）。"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import PROJECT_ROOT
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

_GUIDANCE_CANDIDATES = [
    PROJECT_ROOT / "frontend" / "src" / "config" / "labor" / "guidance.json",
    PROJECT_ROOT / "config" / "labor" / "guidance.json",
]

_FALLBACK = {
    "global_links": [],
    "cause_guidance": {},
    "disclaimer": "指引内容暂不可用，请稍后再试。",
}


def _load_guidance() -> dict:
    for path in _GUIDANCE_CANDIDATES:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load guidance from %s: %s", path, exc)
    return dict(_FALLBACK)


@router.get("")
async def get_guidance(_: User = Depends(get_current_user)):
    """返回维权指引配置（全局链接、案由步骤、免责声明）。"""
    return _load_guidance()
