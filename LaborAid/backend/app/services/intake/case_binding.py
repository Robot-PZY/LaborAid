"""Intake 会话 → 案件 ai_snapshot 绑定与工作流初始化。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.services.intake.session_store import (
    get_user_intake_session,
    session_has_plan,
    upsert_user_intake_session,
)
from app.services.orchestrator.snapshot import get_snapshot, merge_snapshot, record_workflow


def intake_meta_from_analyze(result: dict[str, Any]) -> dict[str, Any]:
    parties = result.get("parties") or {}
    return {
        "cause_type": result.get("cause_type"),
        "cause_label": result.get("cause_label"),
        "channel_id": result.get("channel_id"),
        "scenario_id": result.get("scenario_id"),
        "intake_mode": result.get("intake_mode") or "freeform",
        "structured_answers": result.get("structured_answers") or {},
        "evidence_checklist": list(result.get("evidence_checklist") or []),
        "missing_info": list(result.get("missing_info") or []),
        "summary": result.get("summary") or "",
        "parties": parties,
        "work_region": _extract_work_region(result),
    }


def intake_meta_from_session(session: dict[str, Any]) -> dict[str, Any]:
    answers = session.get("structuredAnswers") or {}
    return {
        "cause_type": session.get("causeType"),
        "cause_label": session.get("causeLabel"),
        "channel_id": session.get("channelId"),
        "scenario_id": session.get("scenarioId"),
        "intake_mode": session.get("intakeMode") or "freeform",
        "structured_answers": answers if isinstance(answers, dict) else {},
        "evidence_checklist": list(session.get("evidenceChecklist") or []),
        "missing_info": list(session.get("missingInfo") or []),
        "summary": session.get("summary") or session.get("caseFacts") or "",
        "parties": session.get("parties") or {},
        "work_region": _extract_work_region_from_answers(answers),
    }


def _extract_work_region(result: dict[str, Any]) -> str | None:
    answers = result.get("structured_answers") or {}
    if isinstance(answers, dict):
        region = _extract_work_region_from_answers(answers)
        if region:
            return region
    return None


def _extract_work_region_from_answers(answers: dict[str, Any]) -> str | None:
    raw = answers.get("work_region")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def get_case_intake(case: Case) -> dict[str, Any]:
    intake = get_snapshot(case).get("intake")
    return dict(intake) if isinstance(intake, dict) else {}


def record_intake_on_case(case: Case, intake_meta: dict[str, Any]) -> dict[str, Any]:
    cleaned = {k: v for k, v in intake_meta.items() if v is not None}
    return merge_snapshot(case, {"intake": cleaned})


def resolve_intake_context(
    case: Case,
    session: dict[str, Any] | None,
) -> dict[str, Any]:
    """合并案件 snapshot 与用户 intake 会话（snapshot 优先）。"""
    snap = get_case_intake(case)
    sess = session or {}
    linked_id = sess.get("createdCaseId")
    session_applies = not linked_id or linked_id == case.id

    cause_type = snap.get("cause_type") or (sess.get("causeType") if session_applies else None)
    channel_id = snap.get("channel_id") or (sess.get("channelId") if session_applies else None)
    scenario_id = snap.get("scenario_id") or (sess.get("scenarioId") if session_applies else None)
    summary = snap.get("summary") or (
        (sess.get("summary") or sess.get("caseFacts")) if session_applies else None
    )
    checklist = snap.get("evidence_checklist") or (
        list(sess.get("evidenceChecklist") or []) if session_applies else []
    )
    has_plan = bool(snap) or (session_has_plan(sess) if session_applies else False)

    return {
        "cause_type": cause_type,
        "channel_id": channel_id,
        "scenario_id": scenario_id,
        "summary": summary,
        "evidence_checklist": list(checklist or []),
        "has_intake_plan": has_plan,
        "work_region": snap.get("work_region") or _extract_work_region_from_answers(
            sess.get("structuredAnswers") or {}
        ),
    }


async def bind_intake_to_new_case(
    db: AsyncSession,
    case: Case,
    user_id: int,
    *,
    cause_type_override: str | None = None,
) -> None:
    """建案后写入 intake 快照、关联 session、初始化 workflow。"""
    row = await get_user_intake_session(db, user_id)
    session = dict(row.session_data) if row and isinstance(row.session_data, dict) else {}

    meta = intake_meta_from_session(session) if session else {}
    if cause_type_override:
        meta["cause_type"] = cause_type_override
    if meta.get("cause_type") or meta.get("evidence_checklist"):
        record_intake_on_case(case, meta)

    if session and session_has_plan(session):
        session["createdCaseId"] = case.id
        await upsert_user_intake_session(db, user_id, session)

    await init_workflow_on_case(db, case, user_id)


async def init_workflow_on_case(db: AsyncSession, case: Case, user_id: int) -> None:
    from app.services.orchestrator.gather import build_case_work_context
    from app.services.workflow import build_case_workflow_payload

    ctx = await build_case_work_context(db, case, user_id=user_id)
    payload = build_case_workflow_payload(ctx)
    record_workflow(case, payload)
