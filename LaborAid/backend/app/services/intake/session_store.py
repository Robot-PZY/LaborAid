"""维权前台咨询方案 — 按用户持久化。"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_intake_plan import UserIntakePlan


def analyzer_result_to_session(
    result: dict,
    *,
    input_text: str = "",
    case_facts: str = "",
    session_id: str | None = None,
) -> dict:
    """将分析 API 结果转为前端 IntakeSession 结构（camelCase）。"""
    tools = result.get("recommended_tools") or []
    return {
        "id": session_id or f"intake_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "causeType": result.get("cause_type", ""),
        "causeLabel": result.get("cause_label", ""),
        "summary": result.get("summary", ""),
        "parties": result.get("parties") or {},
        "missingInfo": result.get("missing_info") or [],
        "evidenceChecklist": result.get("evidence_checklist") or [],
        "recommendedTools": [
            {
                "agent_id": t.get("agent_id", ""),
                "priority": t.get("priority", 0),
                "reason": t.get("reason", ""),
                "action": t.get("action", ""),
                "prefill": t.get("prefill") or {},
            }
            for t in tools
        ],
        "officialLinks": result.get("official_links") or [],
        "credibility": result.get("credibility") or {
            "score": 0,
            "needs_human_review": True,
            "reason": "",
        },
        "searchQuery": result.get("search_query", ""),
        "caseFacts": case_facts or input_text,
        "inputText": input_text,
        "channelId": result.get("channel_id"),
        "scenarioId": result.get("scenario_id"),
        "actionPlan": result.get("action_plan"),
        "currentStep": (result.get("action_plan") or {}).get("current_step", 1),
        "createdCaseId": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def session_has_plan(data: dict | None) -> bool:
    if not data:
        return False
    plan = data.get("actionPlan")
    if isinstance(plan, dict) and plan.get("steps"):
        return True
    return bool(data.get("recommendedTools"))


async def get_user_intake_session(db: AsyncSession, user_id: int) -> UserIntakePlan | None:
    result = await db.execute(
        select(UserIntakePlan).where(UserIntakePlan.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_user_intake_session(
    db: AsyncSession,
    user_id: int,
    session_data: dict,
) -> UserIntakePlan:
    if not session_has_plan(session_data):
        raise ValueError("empty_intake_plan")

    row = await get_user_intake_session(db, user_id)
    now = datetime.now(timezone.utc)
    payload = {**session_data, "updatedAt": now.isoformat()}
    if not payload.get("createdAt"):
        payload["createdAt"] = now.isoformat()

    if row:
        row.session_data = payload
        row.updated_at = now
    else:
        row = UserIntakePlan(user_id=user_id, session_data=payload, created_at=now, updated_at=now)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_user_intake_session(db: AsyncSession, user_id: int) -> bool:
    row = await get_user_intake_session(db, user_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True
