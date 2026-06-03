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


@lru_cache(maxsize=1)
def get_intake_scenarios_config() -> dict:
    data = load_labor_json("intake-scenarios.json", default={})
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def get_special_channels_raw() -> dict:
    data = load_labor_json("special-channels.json", default={})
    return data if isinstance(data, dict) else {}


def get_intake_scenario_meta(channel_id: str, scenario_id: str) -> dict:
    """合并 intake-scenarios 与 special-channels 中的场景定义。"""
    cfg = get_intake_scenarios_config()
    key = f"{channel_id}:{scenario_id}"
    scenario_meta = dict((cfg.get("scenarios") or {}).get(key) or {})
    channel_common = list((cfg.get("channels") or {}).get(channel_id, {}).get("common_fields") or [])
    scenario_meta.setdefault("common_fields", channel_common)
    if "form_fields" not in scenario_meta:
        scenario_meta["form_fields"] = []
    return scenario_meta


def get_special_channel_scenario(channel_id: str, scenario_id: str) -> tuple[dict | None, dict | None, dict]:
    """返回 (channel, scenario, merged_meta)。"""
    raw = get_special_channels_raw()
    channels = raw.get("channels") or {}
    channel = channels.get(channel_id)
    if not channel:
        return None, None, get_intake_scenario_meta(channel_id, scenario_id)

    scenario = None
    for s in channel.get("scenarios") or []:
        if s.get("id") == scenario_id:
            scenario = s
            break

    meta = get_intake_scenario_meta(channel_id, scenario_id)
    if scenario and scenario.get("evidence_checklist"):
        meta["evidence_checklist"] = scenario["evidence_checklist"]
    return channel, scenario, meta
