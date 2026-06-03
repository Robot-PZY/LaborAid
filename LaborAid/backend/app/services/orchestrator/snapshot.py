"""案件 ai_snapshot 读写 — 持久化编排 Agent 状态。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.case import Case


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_snapshot(case: Case) -> dict[str, Any]:
    if isinstance(case.ai_snapshot, dict):
        return dict(case.ai_snapshot)
    return {}


def merge_snapshot(case: Case, patch: dict[str, Any]) -> dict[str, Any]:
    base = get_snapshot(case)
    for key, value in patch.items():
        if key == "doc_pipeline_runs" and isinstance(value, list):
            existing = base.get("doc_pipeline_runs") or []
            if isinstance(existing, list):
                base["doc_pipeline_runs"] = (existing + value)[-10:]
            else:
                base["doc_pipeline_runs"] = value[-10:]
        else:
            base[key] = value
    base["updated_at"] = _utc_iso()
    case.ai_snapshot = base
    return base


def record_next_step(case: Case, step_payload: dict[str, Any]) -> None:
    merge_snapshot(
        case,
        {
            "last_next_step": {
                **step_payload,
                "recorded_at": _utc_iso(),
            },
        },
    )


def record_agent_evaluations(case: Case, agents_payload: dict[str, Any]) -> None:
    merge_snapshot(
        case,
        {
            "agents": {
                "active_agent_id": agents_payload.get("active_agent_id"),
                "items": agents_payload.get("agents") or [],
                "handoffs": agents_payload.get("handoffs") or [],
                "supervisor_summary": agents_payload.get("supervisor_summary"),
                "recorded_at": _utc_iso(),
            },
        },
    )


def record_workflow(case: Case, workflow_payload: dict[str, Any]) -> None:
    merge_snapshot(
        case,
        {
            "workflow": {
                "current_stage": workflow_payload.get("current_stage"),
                "progress": workflow_payload.get("progress"),
                "steps": workflow_payload.get("steps") or [],
                "summary": workflow_payload.get("summary"),
                "recorded_at": _utc_iso(),
            },
        },
    )


def append_pipeline_run(case: Case, run: dict[str, Any]) -> None:
    run = {**run, "recorded_at": _utc_iso()}
    merge_snapshot(case, {"doc_pipeline_runs": [run]})
