"""管理端：系统统计、用户管理（模型与系统配置走 /llm-settings 等，需 admin 角色）。"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, require_admin
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.research import ResearchReport
from app.schemas.admin import AdminStatsOverview, AdminUserOut, AdminUserUpdate
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm
from app.services.system_user import get_system_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/overview", response_model=AdminStatsOverview)
async def stats_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    users_total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    users_active = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))  # noqa: E712
    ).scalar() or 0
    users_new_7d = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= week_ago))
    ).scalar() or 0
    cases_total = (await db.execute(select(func.count(Case.id)))).scalar() or 0
    documents_total = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    evidence_total = (await db.execute(select(func.count(Evidence.id)))).scalar() or 0
    research_total = (
        await db.execute(select(func.count(ResearchReport.id)))
    ).scalar() or 0
    research_reports_7d = (
        await db.execute(
            select(func.count(ResearchReport.id)).where(ResearchReport.created_at >= week_ago)
        )
    ).scalar() or 0

    cases_with_description = (
        await db.execute(
            select(func.count(Case.id)).where(
                Case.description.isnot(None),
                Case.description != "",
            )
        )
    ).scalar() or 0

    cases_with_evidence = (
        await db.execute(select(func.count(func.distinct(Evidence.case_id))))
    ).scalar() or 0

    cases_material_ready = (
        await db.execute(
            select(func.count(Case.id)).where(
                Case.description.isnot(None),
                Case.description != "",
                or_(
                    exists(select(1).where(Evidence.case_id == Case.id)),
                    exists(select(1).where(Document.case_id == Case.id)),
                ),
            )
        )
    ).scalar() or 0

    evidence_with_ocr = (
        await db.execute(
            select(func.count(Evidence.id)).where(
                Evidence.ocr_text.isnot(None),
                Evidence.ocr_text != "",
            )
        )
    ).scalar() or 0
    evidence_ocr_rate_pct = (
        round(100 * evidence_with_ocr / evidence_total) if evidence_total else 0
    )
    material_ready_rate_pct = (
        round(100 * cases_material_ready / cases_total) if cases_total else 0
    )

    system = await get_system_user(db)
    text_llm = await resolve_user_llm(db, system)
    from app.services.llm_profiles import is_vision_profile

    vision_llm = await resolve_vision_llm(db, system)

    return AdminStatsOverview(
        users_total=users_total,
        users_active=users_active,
        users_new_7d=users_new_7d,
        cases_total=cases_total,
        documents_total=documents_total,
        evidence_total=evidence_total,
        research_total=research_total,
        llm_configured=bool(text_llm.api_key),
        vision_llm_configured=bool(vision_llm.api_key)
        and vision_llm.client is not None
        and is_vision_profile(vision_llm.config_name, vision_llm.model),
        cases_with_description=cases_with_description,
        cases_with_evidence=cases_with_evidence,
        cases_material_ready=cases_material_ready,
        evidence_with_ocr=evidence_with_ocr,
        evidence_ocr_rate_pct=evidence_ocr_rate_pct,
        research_reports_7d=research_reports_7d,
        material_ready_rate_pct=material_ready_rate_pct,
    )


@router.get("/stats/usage-trend")
async def usage_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """近 N 日各模块新增数量（按 created_at 日期聚合）。"""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    async def _count_by_day(model, date_col):
        rows = await db.execute(
            select(func.date(date_col), func.count())
            .where(date_col >= start)
            .group_by(func.date(date_col))
        )
        return {str(d): c for d, c in rows.all() if d}

    cases = await _count_by_day(Case, Case.created_at)
    docs = await _count_by_day(Document, Document.created_at)
    ev = await _count_by_day(Evidence, Evidence.created_at)
    res = await _count_by_day(ResearchReport, ResearchReport.created_at)

    trend = []
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).date().isoformat()
        trend.append({
            "date": d,
            "cases": cases.get(d, 0),
            "documents": docs.get(d, 0),
            "evidence": ev.get(d, 0),
            "research": res.get(d, 0),
        })
    return trend


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    from app.services.system_user import SYSTEM_USER_EMAIL

    result = await db.execute(
        select(User)
        .where(User.email != SYSTEM_USER_EMAIL)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from app.services.system_user import SYSTEM_USER_EMAIL

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.email == SYSTEM_USER_EMAIL:
        raise HTTPException(404, "用户不存在")

    if data.role is not None:
        if data.role not in ("admin", "lawyer", "assistant"):
            raise HTTPException(400, "无效的角色")
        if user.id == current_user.id and data.role != "admin":
            raise HTTPException(400, "不能取消自己的管理员权限")
        user.role = data.role

    if data.is_active is not None:
        if user.id == current_user.id and not data.is_active:
            raise HTTPException(400, "不能禁用当前登录账号")
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/performance")
async def admin_performance(_: User = Depends(get_current_admin)):
    from app.core.monitoring import get_performance_summary
    return get_performance_summary()
