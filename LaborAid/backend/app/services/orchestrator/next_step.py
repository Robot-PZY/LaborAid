"""案件维权编排 — Supervisor 调度各专项智能体（规则驱动，可扩展 LLM）。"""

from __future__ import annotations

from typing import Any

from app.services.agents.routes import build_agent_route
from app.services.agents.supervisor import compute_case_next_step as _supervisor_next_step
from app.services.orchestrator.case_context import CaseWorkContext

# 向后兼容：pipeline_tasks 等仍从此模块引用
_AGENT_ROUTES = {
    "guidance": "/guidance",
    "evidence": "/evidence",
    "docgen": "/documents",
    "research": "/research",
    "cases": "/cases",
    "contract": "/contracts",
    "search": "/search",
    "records": "/records",
}


def _build_route(agent_id: str, case_id: int, prefill: dict | None = None) -> str:
    return build_agent_route(agent_id, case_id, prefill)


def compute_case_next_step(ctx: CaseWorkContext) -> dict[str, Any]:
    return _supervisor_next_step(ctx)


__all__ = ["compute_case_next_step", "_build_route", "_AGENT_ROUTES"]
