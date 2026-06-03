"""聚合案件数据，构建编排上下文。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.research import ResearchReport
from app.services.case_readiness import build_case_readiness
from app.services.intake.case_binding import resolve_intake_context
from app.services.intake.session_store import get_user_intake_session
from app.services.orchestrator.case_context import CaseWorkContext


async def build_case_work_context(
    db: AsyncSession,
    case: Case,
    *,
    user_id: int,
    chain_completeness_score: int | None = None,
) -> CaseWorkContext:
    docs_count = int(
        (
            await db.execute(
                select(func.count(Document.id)).where(Document.case_id == case.id)
            )
        ).scalar()
        or 0
    )
    evid_count = int(
        (
            await db.execute(
                select(func.count(Evidence.id)).where(Evidence.case_id == case.id)
            )
        ).scalar()
        or 0
    )
    evid_ocr_count = int(
        (
            await db.execute(
                select(func.count(Evidence.id)).where(
                    Evidence.case_id == case.id,
                    Evidence.ocr_text.isnot(None),
                    Evidence.ocr_text != "",
                )
            )
        ).scalar()
        or 0
    )
    research_count = int(
        (
            await db.execute(
                select(func.count(ResearchReport.id)).where(
                    ResearchReport.case_id == case.id,
                    ResearchReport.owner_id == user_id,
                )
            )
        ).scalar()
        or 0
    )
    evid_rows = (
        await db.execute(select(Evidence).where(Evidence.case_id == case.id))
    ).scalars().all()

    intake_row = await get_user_intake_session(db, user_id)
    session = (
        intake_row.session_data
        if intake_row and isinstance(intake_row.session_data, dict)
        else None
    )
    ctx_intake = resolve_intake_context(case, session)

    readiness = build_case_readiness(
        case,
        documents_count=docs_count,
        evidence_count=evid_count,
        evidence_with_ocr_count=evid_ocr_count,
        evidences=list(evid_rows),
        intake_cause_type=ctx_intake["cause_type"],
        intake_checklist=ctx_intake["evidence_checklist"] or None,
        chain_completeness_score=chain_completeness_score,
    )

    return CaseWorkContext(
        case=case,
        documents_count=docs_count,
        evidence_count=evid_count,
        research_reports_count=research_count,
        intake_cause_type=ctx_intake["cause_type"],
        channel_id=ctx_intake["channel_id"],
        scenario_id=ctx_intake["scenario_id"],
        intake_summary=ctx_intake["summary"],
        has_intake_plan=ctx_intake["has_intake_plan"],
        readiness=readiness,
    )
