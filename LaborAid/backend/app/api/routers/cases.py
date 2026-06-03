import logging
import io
import zipfile
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, func, or_, and_, false as sa_false
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.config import get_settings
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseOut,
    CaseReportRequest,
    CaseReadinessOut,
)
from app.services.case_readiness import build_case_readiness
from app.services.intake.session_store import get_user_intake_session
from app.schemas.research import ResearchReportOut

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CASE_TYPES = {
    "civil_litigation", "criminal_defense", "non_litigation", "administrative_labor",
}
MAX_DESCRIPTION_LENGTH = 50000


def _case_to_out(case: Case, doc_count: int = 0) -> dict:
    return {
        "id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "case_type": case.case_type,
        "court": case.court,
        "status": case.status,
        "plaintiff": case.plaintiff,
        "defendant": case.defendant,
        "description": case.description,
        "owner_id": case.owner_id,
        "team_id": case.team_id,
        "filing_date": case.filing_date,
        "hearing_dates": case.hearing_dates,
        "deadline_dates": case.deadline_dates,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "document_count": doc_count,
    }


@router.get("")
async def list_cases(
    status: str | None = None,
    case_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    doc_count_sq = (
        select(func.count(Document.id))
        .where(Document.case_id == Case.id)
        .correlate(Case)
        .scalar_subquery()
        .label("document_count")
    )

    base_where = or_(
        Case.owner_id == current_user.id,
        and_(
            Case.team_id == current_user.team_id,
        ) if current_user.team_id is not None else sa_false(),
    )

    # Count query for pagination header
    count_q = select(func.count(Case.id)).where(base_where)
    if status:
        count_q = count_q.where(Case.status == status)
    if case_type:
        count_q = count_q.where(Case.case_type == case_type)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Case, doc_count_sq)
        .where(base_where)
    )
    if status:
        q = q.where(Case.status == status)
    if case_type:
        q = q.where(Case.case_type == case_type)
    q = q.order_by(Case.updated_at.desc()).offset(skip).limit(limit)

    try:
        result = await db.execute(q)
        rows = result.all()
        items = [CaseOut.model_validate(_case_to_out(case, count)).model_dump(mode="json") for case, count in rows]
        return JSONResponse(
            content=items,
            headers={"X-Total-Count": str(total)},
        )
    except Exception as e:
        logger.error(f"List cases failed: {e}")
        raise HTTPException(500, "查询案件列表失败")


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    data: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.case_type not in ALLOWED_CASE_TYPES:
        raise HTTPException(400, f"无效的案件类型，允许值: {', '.join(sorted(ALLOWED_CASE_TYPES))}")

    if data.filing_date:
        try:
            filing = datetime.strptime(data.filing_date, "%Y-%m-%d").date()
            if filing > date.today():
                raise HTTPException(400, "立案日期不能是未来日期")
        except ValueError:
            raise HTTPException(400, "立案日期格式无效，请使用 YYYY-MM-DD 格式")

    if data.description and len(data.description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(400, f"案件描述不能超过 {MAX_DESCRIPTION_LENGTH} 个字符")

    try:
        case = Case(
            **data.model_dump(),
            owner_id=current_user.id,
            team_id=current_user.team_id,
        )
        db.add(case)
        await db.flush()
        await db.refresh(case)
        return CaseOut.model_validate(_case_to_out(case, 0))
    except Exception as e:
        logger.error(f"Create case failed: {e}")
        await db.rollback()
        raise HTTPException(500, "创建案件失败，请稍后重试")


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        case = await db.get(Case, case_id)
        if not case or (case.owner_id != current_user.id and (not current_user.team_id or case.team_id != current_user.team_id)):
            raise HTTPException(404, "案件不存在")
        doc_count = await db.execute(
            select(func.count()).where(Document.case_id == case.id)
        )
        return CaseOut.model_validate(_case_to_out(case, doc_count.scalar() or 0))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get case failed: {e}")
        raise HTTPException(500, "查询案件失败")


@router.put("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: int,
    data: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        case = await db.get(Case, case_id)
        if not case or case.owner_id != current_user.id:
            raise HTTPException(404, "案件不存在")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(case, k, v)
        await db.flush()
        await db.refresh(case)
        doc_count = await db.execute(
            select(func.count()).where(Document.case_id == case.id)
        )
        return CaseOut.model_validate(_case_to_out(case, doc_count.scalar() or 0))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update case failed: {e}")
        await db.rollback()
        raise HTTPException(500, "更新案件失败")


async def _get_accessible_case(case_id: int, current_user: User, db: AsyncSession) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "案件不存在")
    if case.owner_id != current_user.id and (
        not current_user.team_id or case.team_id != current_user.team_id
    ):
        raise HTTPException(404, "案件不存在")
    return case


@router.get("/{case_id}/materials")
async def get_case_materials(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """返回案件已关联材料概况，供案情分析页展示。"""
    case = await _get_accessible_case(case_id, current_user, db)
    from app.services.research.case_analysis import gather_case_materials

    materials = await gather_case_materials(db, case, owner_id=current_user.id)
    stats = materials["stats"]
    return {
        "case_id": case.id,
        "case_title": case.title,
        "has_description": stats["has_description"],
        "documents_count": stats["documents"],
        "evidence_count": stats["evidence"],
        "documents": [
            {"id": d.id, "title": d.title, "type": d.type, "status": d.status, "updated_at": d.updated_at.isoformat()}
            for d in materials["documents"]
        ],
        "evidence": [
            {
                "id": e.id,
                "title": e.title,
                "evidence_type": e.type,
                "has_ocr": bool((e.ocr_text or "").strip()),
            }
            for e in materials["evidence"]
        ],
        "ready_for_analysis": bool(
            stats["has_description"] or stats["documents"] > 0 or stats["evidence"] > 0
        ),
    }


@router.get("/{case_id}/readiness", response_model=CaseReadinessOut)
async def get_case_readiness(
    case_id: int,
    chain_score: int | None = Query(
        None,
        ge=0,
        le=100,
        description="证据链分析得分，用于与材料完整度加权合并",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """计算案件 AI 就绪度，返回缺失项与下一步建议。"""
    case = await _get_accessible_case(case_id, current_user, db)

    docs_count_q = await db.execute(
        select(func.count(Document.id)).where(Document.case_id == case.id)
    )
    evid_count_q = await db.execute(
        select(func.count(Evidence.id)).where(Evidence.case_id == case.id)
    )
    evid_ocr_count_q = await db.execute(
        select(func.count(Evidence.id)).where(
            Evidence.case_id == case.id,
            Evidence.ocr_text.isnot(None),
            Evidence.ocr_text != "",
        )
    )
    evid_rows = (
        await db.execute(select(Evidence).where(Evidence.case_id == case.id))
    ).scalars().all()

    intake_cause: str | None = None
    intake_row = await get_user_intake_session(db, current_user.id)
    if intake_row and isinstance(intake_row.session_data, dict):
        session = intake_row.session_data
        if session.get("createdCaseId") == case.id:
            intake_cause = session.get("causeType") or None

    return build_case_readiness(
        case,
        documents_count=int(docs_count_q.scalar() or 0),
        evidence_count=int(evid_count_q.scalar() or 0),
        evidence_with_ocr_count=int(evid_ocr_count_q.scalar() or 0),
        evidences=list(evid_rows),
        intake_cause_type=intake_cause,
        chain_completeness_score=chain_score,
    )


@router.post("/{case_id}/case-report", response_model=ResearchReportOut)
async def create_case_analysis_report(
    case_id: int,
    data: CaseReportRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """汇总案件已知信息，生成案情分析总结报告并保存。"""
    from app.core.security import check_rate_limit
    from app.models.research import ResearchReport
    from app.services.llm_resolver import resolve_user_llm
    from app.services.research.case_analysis import generate_case_analysis_report

    if not check_rate_limit(f"case_report:{current_user.id}", max_requests=10, window_seconds=3600):
        raise HTTPException(429, "案情分析请求过于频繁，请一小时后再试")

    case = await _get_accessible_case(case_id, current_user, db)
    extra = (data.extra_notes if data else None) or None

    try:
        llm = await resolve_user_llm(db, current_user)
        result = await generate_case_analysis_report(
            db, case, owner_id=current_user.id, llm=llm, extra_notes=extra
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    row = ResearchReport(
        owner_id=current_user.id,
        query=result["query"],
        report=result["report"],
        sources_used=result["sources_used"],
        case_id=case.id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    out = ResearchReportOut.model_validate(row).model_dump(mode="json")
    out["conclusion_level"] = result.get("conclusion_level")
    return out


@router.delete("/{case_id}")
async def delete_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除案件（关联证据一并删除；文书/报告仅解除关联）。"""
    case = await db.get(Case, case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(404, "案件不存在或无权删除")
    try:
        await db.delete(case)
        await db.flush()
        return {"message": "案件已删除", "id": case_id}
    except Exception as e:
        logger.exception("Delete case failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除案件失败")


@router.post("/{case_id}/analyze")
async def analyze_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 分析案件：提取当事人、案由、关键时间、争议焦点、策略建议。"""
    case = await db.get(Case, case_id)
    if not case or (case.owner_id != current_user.id and (not current_user.team_id or case.team_id != current_user.team_id)):
        raise HTTPException(404, "案件不存在")

    if not case.description:
        raise HTTPException(400, "案件描述为空，无法分析")

    from app.services.llm_resolver import resolve_user_llm

    llm = await resolve_user_llm(db, current_user)

    prompt = f"""请分析以下案件，输出结构化的法律分析报告：

## 案件信息
标题：{case.title}
类型：{case.case_type}
原告：{case.plaintiff or '未知'}
被告：{case.defendant or '未知'}
描述：{case.description}

## 请输出以下内容（用 Markdown 格式）：
1. **案件概要** — 一句话概括案件核心
2. **当事人信息** — 原被告基本信息及法律地位
3. **案由认定** — 案由及法律关系分析
4. **关键时间节点** — 诉讼时效、重要日期提醒
5. **争议焦点** — 双方核心争议点
6. **适用法条** — 相关法律法规引用
7. **诉讼策略建议** — 原告/被告各应如何应对
8. **风险评估** — 胜诉概率及风险提示"""

    try:
        response = await llm.client.messages.create(
            model=llm.model,
            max_tokens=llm.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = response.content[0].text if response.content else ""
    except Exception as e:
        logger.error(f"Case analysis failed for {case_id}: {e}")
        raise HTTPException(503, f"AI分析失败: {str(e)[:200]}")

    return {"case_id": case_id, "analysis": analysis}


@router.get("/{case_id}/export-pack")
async def export_case_pack(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出案件材料包（案情摘要 + 文书 + 证据文件）。"""
    case = await db.get(Case, case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(404, "案件不存在")

    settings = get_settings()
    docs = (await db.execute(select(Document).where(Document.case_id == case_id))).scalars().all()
    evidence_rows = (await db.execute(select(Evidence).where(Evidence.case_id == case_id))).scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = f"""# 劳权智助 · 案件材料包

案件标题：{case.title}
案件类型：{case.case_type}
原告/申请人：{case.plaintiff or '—'}
被告/被申请人：{case.defendant or '—'}
导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

## 案情描述
{case.description or '（无）'}

---
免责声明：本材料包由 AI 辅助整理，不构成法律意见。办事要求以当地仲裁委、人社部门最新规定为准。
"""
        zf.writestr("README.txt", readme.encode("utf-8"))

        for i, doc in enumerate(docs, 1):
            safe_title = (doc.title or f"文书{i}")[:80].replace("/", "-")
            content = doc.content or ""
            zf.writestr(f"文书/{i}_{safe_title}.md", content.encode("utf-8"))

        for ev in evidence_rows:
            if ev.file_path:
                fp = settings.upload_path / ev.file_path
                if fp.is_file():
                    arc = f"证据/{ev.id}_{fp.name}"
                    zf.write(fp, arcname=arc)
            if ev.ocr_text:
                title = (ev.title or f"证据{ev.id}")[:60].replace("/", "-")
                zf.writestr(f"证据/{ev.id}_{title}_OCR.txt", ev.ocr_text.encode("utf-8"))

    buf.seek(0)
    filename = f"case_{case_id}_materials.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
