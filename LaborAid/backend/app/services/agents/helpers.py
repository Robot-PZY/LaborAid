"""案件上下文 — 各智能体共享的派生字段。"""

from __future__ import annotations

from app.services.orchestrator.case_context import CaseWorkContext


def cause_type(ctx: CaseWorkContext) -> str:
    r = ctx.readiness
    return r.cause_type or ctx.intake_cause_type or "wage_arrears"


def cause_label(ctx: CaseWorkContext) -> str:
    return ctx.readiness.cause_label or "劳动争议"


def combined_score(ctx: CaseWorkContext) -> int:
    r = ctx.readiness
    return r.combined_score if r.combined_score is not None else r.readiness_score


def required_missing(ctx: CaseWorkContext) -> list[str]:
    return [
        s.item
        for s in (ctx.readiness.evidence_suggestions or [])
        if s.priority == "required" and s.status == "missing"
    ]


def common_blockers(ctx: CaseWorkContext) -> list[str]:
    r = ctx.readiness
    blockers: list[str] = []
    blockers.extend(r.docgen_blockers or [])
    blockers.extend(r.missing_items[:3])
    return blockers


def prefill_doc(ctx: CaseWorkContext) -> dict:
    case = ctx.case
    c = cause_type(ctx)
    return {
        "docType": "application",
        "causeType": c,
        "caseFacts": (case.description or ctx.intake_summary or "")[:800],
    }
