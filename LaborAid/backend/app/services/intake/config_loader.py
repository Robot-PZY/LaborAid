"""Load labor-rights JSON configs shared with the frontend."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

_LABOR_DIR_CANDIDATES = [
    PROJECT_ROOT / "frontend" / "src" / "config" / "labor",
    PROJECT_ROOT / "config" / "labor",
]


def _resolve_labor_dir() -> Path | None:
    for d in _LABOR_DIR_CANDIDATES:
        if d.is_dir():
            return d
    return None


def load_labor_json(name: str, default=None):
    labor_dir = _resolve_labor_dir()
    if not labor_dir:
        return default if default is not None else {}
    path = labor_dir / name
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return default if default is not None else {}


@lru_cache(maxsize=1)
def get_causes() -> list[dict]:
    data = load_labor_json("causes.json", default=[])
    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def get_evidence_checklists() -> dict:
    data = load_labor_json("evidence-checklist.json", default={})
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def get_guidance_links() -> list[dict]:
    guidance = load_labor_json("guidance.json", default={})
    if isinstance(guidance, dict):
        return guidance.get("global_links") or []
    return []
