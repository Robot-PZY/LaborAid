"""智能体 id → 前端路由（与 frontend/src/config/agents.ts 对齐）。"""

from __future__ import annotations

AGENT_ROUTES: dict[str, str] = {
    "guidance": "/guidance",
    "evidence": "/evidence",
    "docgen": "/documents",
    "research": "/research",
    "cases": "/cases",
    "contract": "/contracts",
    "search": "/search",
    "records": "/records",
}


def build_agent_route(agent_id: str, case_id: int, prefill: dict | None = None) -> str:
    prefill = prefill or {}
    base = AGENT_ROUTES.get(agent_id, "/")
    if agent_id == "guidance":
        cause = prefill.get("cause") or prefill.get("causeType")
        return f"{base}?cause={cause}" if cause else base
    if agent_id == "evidence":
        return f"{base}?caseId={case_id}"
    if agent_id == "research":
        return f"{base}?caseId={case_id}"
    if agent_id == "docgen":
        parts = ["worker=1"]
        if case_id:
            parts.append(f"caseId={case_id}")
        doc_type = prefill.get("docType") or prefill.get("doc_type")
        if doc_type:
            parts.append(f"type={doc_type}")
        cause = prefill.get("cause") or prefill.get("causeType")
        if cause:
            parts.append(f"cause={cause}")
        return f"{base}?{'&'.join(parts)}"
    if agent_id == "cases":
        return f"{base}?open={case_id}"
    if agent_id == "contract":
        return f"{base}?caseId={case_id}" if case_id else base
    return base


def alt_step(
    agent_id: str,
    label: str,
    reason: str,
    ctx,
    prefill: dict | None = None,
) -> dict:
    from app.services.orchestrator.case_context import CaseWorkContext

    assert isinstance(ctx, CaseWorkContext)
    return {
        "agent_id": agent_id,
        "label": label,
        "route": build_agent_route(agent_id, ctx.case.id, prefill),
        "reason": reason,
    }
