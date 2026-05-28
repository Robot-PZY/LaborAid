"""法律研究路由"""

import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, check_rate_limit
from app.config import get_settings
from app.models.user import User
from app.models.research import ResearchReport
from app.schemas.research import ResearchRequest, ResearchReportOut, ResearchExport
from app.services.research.engine import LegalResearchEngine
from app.services.llm_resolver import resolve_user_llm

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ResearchReportOut)
async def create_research(
    data: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.query or not data.query.strip():
        raise HTTPException(400, "研究问题不能为空")

    # Rate limit research: 10 per hour per user
    if not check_rate_limit(f"research:{current_user.id}", max_requests=10, window_seconds=3600):
        raise HTTPException(429, "研究请求过于频繁，请一小时后再试")

    try:
        import time
        start = time.time()
        llm = await resolve_user_llm(db, current_user)
        engine = LegalResearchEngine()
        result = await engine.research(data.query.strip(), data.sources, data.case_id, llm=llm)
        logger.info("Research completed in %.2fs", time.time() - start)

        row = ResearchReport(
            owner_id=current_user.id,
            query=data.query.strip(),
            report=result["report"],
            sources_used=result["sources_used"],
            case_id=data.case_id,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return ResearchReportOut.model_validate(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create research failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "法律研究失败，请稍后重试")


@router.get("")
async def list_research(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        base_where = ResearchReport.owner_id == current_user.id
        if case_id is not None:
            base_where = and_(base_where, ResearchReport.case_id == case_id)
        # Count query for pagination header
        total = (await db.execute(
            select(func.count(ResearchReport.id)).where(base_where)
        )).scalar() or 0

        result = await db.execute(
            select(ResearchReport)
            .where(base_where)
            .order_by(ResearchReport.created_at.desc())
            .offset(skip).limit(limit)
        )
        items = result.scalars().all()

        # Build response with truncated report text in list view
        response_data = []
        from app.services.research.case_analysis import parse_conclusion_level

        for r in items:
            out = ResearchReportOut.model_validate(r)
            if out.report and len(out.report) > 500:
                out.report = out.report[:500] + "..."
            payload = out.model_dump(mode="json")
            payload["conclusion_level"] = parse_conclusion_level(r.report or "")
            response_data.append(payload)

        return JSONResponse(
            content=response_data,
            headers={"X-Total-Count": str(total)},
        )
    except Exception as e:
        logger.error("List research failed: %s", e)
        raise HTTPException(500, "查询研究报告列表失败")


@router.get("/{report_id}", response_model=ResearchReportOut)
async def get_research(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(ResearchReport).where(ResearchReport.id == report_id, ResearchReport.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "研究报告不存在")
        from app.services.research.case_analysis import parse_conclusion_level

        out = ResearchReportOut.model_validate(row)
        payload = out.model_dump(mode="json")
        payload["conclusion_level"] = parse_conclusion_level(row.report or "")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get research failed: %s", e)
        raise HTTPException(500, "查询研究报告失败")


@router.delete("/{report_id}")
async def delete_research(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(ResearchReport).where(ResearchReport.id == report_id, ResearchReport.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "研究报告不存在")
        await db.delete(row)
        await db.commit()
        return {"message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete research failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除研究报告失败")


@router.post("/{report_id}/export")
async def export_research(
    report_id: int,
    data: ResearchExport,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出研究报告为 Word 或 Markdown 文件。"""
    result = await db.execute(
        select(ResearchReport).where(ResearchReport.id == report_id, ResearchReport.owner_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "研究报告不存在")

    settings = get_settings()
    output_dir = settings.upload_path / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    if data.format == "docx":
        from app.services.docgen.word_export import export_research_to_docx
        filepath = await export_research_to_docx(row, output_dir)
        return FileResponse(
            filepath,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=Path(filepath).name,
        )
    else:
        safe_query = "".join(c for c in row.query[:30] if c.isalnum() or c in "（）()—")
        filepath = output_dir / f"research_{row.id}_{safe_query}.md"
        await asyncio.to_thread(filepath.write_text, f"# {row.query}\n\n{row.report}", "utf-8")
        return FileResponse(
            filepath,
            media_type="text/markdown",
            filename=filepath.name,
        )
