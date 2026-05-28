"""用户门户：个人使用概览与最近动态。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.case import Case
from app.models.contract import Contract
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.research import ResearchReport
from app.models.user import User
from app.models.user_material import UserMaterial
from app.schemas.user_portal import UserOverview, UserRecentItem

router = APIRouter()


@router.get("/overview", response_model=UserOverview)
async def user_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id

    async def _count_owned(model, *, owner_col="owner_id"):
        return (
            await db.execute(
                select(func.count()).select_from(model).where(getattr(model, owner_col) == uid)
            )
        ).scalar() or 0

    cases_count = await _count_owned(Case)
    documents_count = await _count_owned(Document)
    research_count = await _count_owned(ResearchReport)
    contracts_count = (
        await db.execute(
            select(func.count()).select_from(Contract).where(Contract.owner_id == uid)
        )
    ).scalar() or 0
    evidence_count = (
        await db.execute(
            select(func.count())
            .select_from(Evidence)
            .join(Case, Evidence.case_id == Case.id)
            .where(Case.owner_id == uid)
        )
    ).scalar() or 0

    vault_row = await db.execute(
        select(func.count(UserMaterial.id), func.coalesce(func.sum(UserMaterial.size_bytes), 0)).where(
            UserMaterial.user_id == uid,
            UserMaterial.deleted_at.is_(None),
        )
    )
    vault_files, vault_bytes = vault_row.one()
    vault_files = int(vault_files or 0)
    vault_bytes = int(vault_bytes or 0)

    recent: list[UserRecentItem] = []

    case_rows = (
        await db.execute(
            select(Case.id, Case.title, Case.updated_at)
            .where(Case.owner_id == uid)
            .order_by(Case.updated_at.desc())
            .limit(5)
        )
    ).all()
    for row in case_rows:
        recent.append(
            UserRecentItem(
                id=row.id,
                kind="case",
                title=row.title,
                updated_at=row.updated_at,
            )
        )

    doc_rows = (
        await db.execute(
            select(Document.id, Document.title, Document.updated_at)
            .where(Document.owner_id == uid)
            .order_by(Document.updated_at.desc())
            .limit(5)
        )
    ).all()
    for row in doc_rows:
        recent.append(
            UserRecentItem(
                id=row.id,
                kind="document",
                title=row.title,
                updated_at=row.updated_at,
            )
        )

    ev_rows = (
        await db.execute(
            select(Evidence.id, Evidence.title, Evidence.created_at)
            .join(Case, Evidence.case_id == Case.id)
            .where(Case.owner_id == uid)
            .order_by(Evidence.created_at.desc())
            .limit(5)
        )
    ).all()
    for row in ev_rows:
        recent.append(
            UserRecentItem(
                id=row.id,
                kind="evidence",
                title=row.title or "证据材料",
                updated_at=row.created_at,
            )
        )

    res_rows = (
        await db.execute(
            select(ResearchReport.id, ResearchReport.query, ResearchReport.created_at)
            .where(ResearchReport.owner_id == uid)
            .order_by(ResearchReport.created_at.desc())
            .limit(5)
        )
    ).all()
    for row in res_rows:
        recent.append(
            UserRecentItem(
                id=row.id,
                kind="research",
                title=(row.query[:80] + "…") if len(row.query) > 80 else row.query,
                updated_at=row.created_at,
            )
        )

    contract_rows = (
        await db.execute(
            select(Contract.id, Contract.title, Contract.updated_at)
            .where(Contract.owner_id == uid)
            .order_by(Contract.updated_at.desc())
            .limit(5)
        )
    ).all()
    for row in contract_rows:
        recent.append(
            UserRecentItem(
                id=row.id,
                kind="contract",
                title=row.title,
                updated_at=row.updated_at,
            )
        )

    def _sort_key(item: UserRecentItem) -> datetime:
        t = item.updated_at
        if t.tzinfo is None:
            return t.replace(tzinfo=None)
        return t

    recent.sort(key=_sort_key, reverse=True)
    recent = recent[:8]

    return UserOverview(
        cases=cases_count,
        documents=documents_count,
        evidence=evidence_count,
        research=research_count,
        contracts=contracts_count,
        vault_files=vault_files,
        vault_bytes=vault_bytes,
        recent=recent,
    )
