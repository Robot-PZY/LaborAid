"""案件维权工作流 — 四步 FSM，与协作智能体对齐。"""

from __future__ import annotations

from typing import Any

from app.services.agents.helpers import required_missing
from app.services.agents.routes import build_agent_route
from app.services.agents.supervisor import build_agents_list_payload
from app.services.orchestrator.case_context import CaseWorkContext

# Supervisor pipeline_stage → 工作流 stage
PIPELINE_TO_WORKFLOW: dict[str, str] = {
    "path": "case",
    "evidence": "materials",
    "documents": "documents",
    "research": "report",
    "complete": "complete",
}

WORKFLOW_STEP_DEFS: tuple[dict[str, str], ...] = (
    {
        "id": "case",
        "label": "生成案件",
        "hint": "建立案件档案并补充案情摘要",
        "agent_id": "cases",
    },
    {
        "id": "materials",
        "label": "审查材料",
        "hint": "上传并核对证据、合同等材料",
        "agent_id": "evidence",
    },
    {
        "id": "documents",
        "label": "生成文书",
        "hint": "起草仲裁申请、证据清单等文书",
        "agent_id": "docgen",
    },
    {
        "id": "report",
        "label": "案件报告",
        "hint": "汇总材料生成阶段性案情报告",
        "agent_id": "research",
    },
)


def workflow_stage_from_pipeline(pipeline_stage: str) -> str:
    return PIPELINE_TO_WORKFLOW.get(pipeline_stage, "case")


def _step_done(step_id: str, ctx: CaseWorkContext) -> bool:
    case = ctx.case
    desc = (case.description or "").strip()
    missing = required_missing(ctx)

    if step_id == "case":
        return bool(case.title) and (len(desc) >= 30 or ctx.has_intake_plan or ctx.evidence_count > 0)
    if step_id == "materials":
        return ctx.evidence_count > 0 and not missing
    if step_id == "documents":
        return ctx.documents_count > 0
    if step_id == "report":
        return ctx.research_reports_count > 0
    return False


def _resolve_current_stage(ctx: CaseWorkContext) -> str:
    for step in WORKFLOW_STEP_DEFS:
        if not _step_done(step["id"], ctx):
            return step["id"]
    return "complete"


def _step_route(step_id: str, ctx: CaseWorkContext) -> str:
    cid = ctx.case.id
    if step_id == "case":
        return build_agent_route("cases", cid)
    if step_id == "materials":
        return build_agent_route("evidence", cid)
    if step_id == "documents":
        return build_agent_route(
            "docgen",
            cid,
            {"docType": "application", "causeType": ctx.readiness.cause_type or "wage_arrears"},
        )
    if step_id == "report":
        return build_agent_route("research", cid)
    return build_agent_route("records", cid)


def build_case_workflow_payload(ctx: CaseWorkContext) -> dict[str, Any]:
    current = _resolve_current_stage(ctx)
    agents_payload = build_agents_list_payload(ctx)
    active_agent = agents_payload.get("active_agent_id")

    steps: list[dict[str, Any]] = []
    progress = 0
    for step_def in WORKFLOW_STEP_DEFS:
        sid = step_def["id"]
        done = _step_done(sid, ctx)
        if done:
            status = "done"
            progress += 1
        elif sid == current:
            status = "active"
        else:
            status = "pending"

        steps.append(
            {
                "id": sid,
                "label": step_def["label"],
                "hint": step_def["hint"],
                "status": status,
                "route": _step_route(sid, ctx),
                "agent_id": step_def["agent_id"],
            }
        )

    if current == "complete":
        progress = len(WORKFLOW_STEP_DEFS)

    summary = _workflow_summary(current, progress, ctx)
    ai_hint = agents_payload.get("supervisor_summary") or None

    return {
        "case_id": ctx.case.id,
        "current_stage": current,
        "progress": progress,
        "total_steps": len(WORKFLOW_STEP_DEFS),
        "steps": steps,
        "summary": summary,
        "ai_hint": ai_hint,
        "active_agent_id": active_agent,
    }


def _workflow_summary(current: str, progress: int, ctx: CaseWorkContext) -> str:
    total = len(WORKFLOW_STEP_DEFS)
    if current == "complete":
        return f"「{ctx.case.title}」四步工作流已完成（{total}/{total}）。"
    label = next((s["label"] for s in WORKFLOW_STEP_DEFS if s["id"] == current), current)
    return f"当前阶段：{label}（已完成 {progress}/{total} 步）。"
