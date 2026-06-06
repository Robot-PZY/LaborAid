"""案件维权编排 — Supervisor 调度各专项智能体（LangGraph 状态机驱动）。"""

from __future__ import annotations

import logging
from typing import Any

from app.services.agents.routes import build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext

logger = logging.getLogger(__name__)

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
    """使用 LangGraph Supervisor 状态机计算下一步。

    优先使用 LangGraph 实现，失败时回退到规则驱动实现。
    """
    try:
        from app.services.agents.graph import run_supervisor
        return run_supervisor(ctx)
    except Exception as e:
        logger.warning("LangGraph supervisor failed, falling back to rule-based: %s", e)
        # 回退到原有规则驱动实现
        from app.services.agents.supervisor import compute_case_next_step as _fallback
        return _fallback(ctx)


__all__ = ["compute_case_next_step", "_build_route", "_AGENT_ROUTES"]
