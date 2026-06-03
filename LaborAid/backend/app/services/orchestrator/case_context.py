"""案件工作区上下文 — 编排 Agent 与各 AI 工具共享。"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.case import Case
from app.schemas.case import CaseReadinessOut


@dataclass
class CaseWorkContext:
    case: Case
    documents_count: int
    evidence_count: int
    research_reports_count: int
    intake_cause_type: str | None
    channel_id: str | None
    scenario_id: str | None
    intake_summary: str | None
    has_intake_plan: bool
    readiness: CaseReadinessOut


def context_to_api_dict(ctx: CaseWorkContext) -> dict:
    r = ctx.readiness
    return {
        "case_id": ctx.case.id,
        "cause_type": r.cause_type,
        "cause_label": r.cause_label,
        "channel_id": ctx.channel_id,
        "documents_count": ctx.documents_count,
        "evidence_count": ctx.evidence_count,
        "research_reports_count": ctx.research_reports_count,
        "has_intake_plan": ctx.has_intake_plan,
        "readiness_score": r.readiness_score,
        "combined_score": r.combined_score,
    }
