import json
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
    CaseDocFactsOut,
    CaseDocRecommendationsOut,
    CaseReadinessOut,
)
from app.schemas.orchestrator import (
    CaseAgentAskIn,
    CaseAgentAskOut,
    CaseAgentNextStepOut,
    CaseAgentSnapshotOut,
    CaseAgentsListOut,
    CaseDocPipelineIn,
    CaseWorkflowOut,
)
from app.services.case_readiness import build_case_readiness
from app.services.intake.case_binding import resolve_intake_context
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
            stats["has_description"]
            or stats["documents"] > 0
            or stats["evidence"] > 0
            or stats.get("has_intake_summary")
        ),
    }


@router.get("/{case_id}/doc-recommendations", response_model=CaseDocRecommendationsOut)
async def get_case_doc_recommendations(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分析案情与证据，推荐应生成的文书清单。"""
    from app.services.docgen.recommendations import recommend_docs_for_case

    case = await _get_accessible_case(case_id, current_user, db)
    intake_row = await get_user_intake_session(db, current_user.id)
    session = (
        intake_row.session_data
        if intake_row and isinstance(intake_row.session_data, dict)
        else None
    )
    raw = await recommend_docs_for_case(db, case, intake_session=session)

    # 关联已生成文书的 document_id
    doc_rows = (
        await db.execute(
            select(Document.id, Document.type)
            .where(Document.case_id == case.id)
            .order_by(Document.updated_at.desc())
        )
    ).all()
    type_to_doc: dict[str, int] = {}
    for doc_id, doc_type in doc_rows:
        key = doc_type
        if key and key not in type_to_doc:
            type_to_doc[key] = doc_id

    for item in raw.get("recommendations") or []:
        if item.get("generated"):
            item["document_id"] = type_to_doc.get(item.get("doc_type"))

    return CaseDocRecommendationsOut.model_validate(raw)


@router.get("/{case_id}/doc-facts", response_model=CaseDocFactsOut)
async def get_case_doc_facts(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """聚合案件描述与证据分析，供文书生成预填案情。"""
    from app.services.orchestrator.doc_facts import build_docgen_case_facts

    case = await _get_accessible_case(case_id, current_user, db)
    facts = await build_docgen_case_facts(db, case)
    return CaseDocFactsOut(case_facts=facts)


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

    intake_row = await get_user_intake_session(db, current_user.id)
    session = (
        intake_row.session_data
        if intake_row and isinstance(intake_row.session_data, dict)
        else None
    )
    ctx = resolve_intake_context(case, session)

    return build_case_readiness(
        case,
        documents_count=int(docs_count_q.scalar() or 0),
        evidence_count=int(evid_count_q.scalar() or 0),
        evidence_with_ocr_count=int(evid_ocr_count_q.scalar() or 0),
        evidences=list(evid_rows),
        intake_cause_type=ctx["cause_type"],
        intake_checklist=ctx["evidence_checklist"] or None,
        chain_completeness_score=chain_score,
    )


@router.get("/{case_id}/agent/next-step", response_model=CaseAgentNextStepOut)
async def get_case_agent_next_step(
    case_id: int,
    chain_score: int | None = Query(None, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """维权编排 Agent：根据案件材料状态推荐下一步操作。"""
    from app.services.orchestrator.gather import build_case_work_context
    from app.services.orchestrator import compute_case_next_step

    case = await _get_accessible_case(case_id, current_user, db)
    ctx = await build_case_work_context(
        db,
        case,
        user_id=current_user.id,
        chain_completeness_score=chain_score,
    )
    result = compute_case_next_step(ctx)
    from app.services.orchestrator.snapshot import record_next_step

    record_next_step(case, result)
    await db.flush()
    return CaseAgentNextStepOut.model_validate(result)


@router.get("/{case_id}/agents", response_model=CaseAgentsListOut)
async def get_case_agents(
    case_id: int,
    chain_score: int | None = Query(None, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出案件关联的专项智能体状态（Supervisor 聚合）。"""
    from app.services.agents import build_agents_list_payload
    from app.services.orchestrator.gather import build_case_work_context
    from app.services.orchestrator.snapshot import record_agent_evaluations

    case = await _get_accessible_case(case_id, current_user, db)
    ctx = await build_case_work_context(
        db,
        case,
        user_id=current_user.id,
        chain_completeness_score=chain_score,
    )
    payload = build_agents_list_payload(ctx)
    record_agent_evaluations(case, payload)
    await db.flush()
    return CaseAgentsListOut.model_validate(payload)


@router.get("/{case_id}/workflow", response_model=CaseWorkflowOut)
async def get_case_workflow(
    case_id: int,
    chain_score: int | None = Query(None, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """案件四步工作流：生成案件 → 审查材料 → 生成文书 → 案件报告。"""
    from app.services.orchestrator.gather import build_case_work_context
    from app.services.orchestrator.snapshot import record_workflow
    from app.services.workflow import build_case_workflow_payload

    case = await _get_accessible_case(case_id, current_user, db)
    ctx = await build_case_work_context(
        db,
        case,
        user_id=current_user.id,
        chain_completeness_score=chain_score,
    )
    payload = build_case_workflow_payload(ctx)
    record_workflow(case, payload)
    await db.flush()
    return CaseWorkflowOut.model_validate(payload)


@router.get("/{case_id}/agent/snapshot", response_model=CaseAgentSnapshotOut)
async def get_case_agent_snapshot(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """读取案件 AI 编排快照（下一步记录、流水线历史）。"""
    from app.services.orchestrator.snapshot import get_snapshot

    case = await _get_accessible_case(case_id, current_user, db)
    return CaseAgentSnapshotOut(case_id=case.id, snapshot=get_snapshot(case))


@router.post("/{case_id}/agent/doc-pipeline-stream")
async def case_doc_pipeline_stream(
    case_id: int,
    data: CaseDocPipelineIn,
    current_user: User = Depends(get_current_user),
):
    """文书助手流水线 SSE：检索 → 生成 → 审校 → 质检，并写入 ai_snapshot。"""
    from app.core.security import check_rate_limit
    from app.core.streaming_db import wrap_stream_with_db
    from app.services.orchestrator.doc_pipeline import run_doc_pipeline_stream

    if not check_rate_limit(f"case_doc_pipeline:{current_user.id}", max_requests=6, window_seconds=3600):
        raise HTTPException(429, "文书流水线请求过于频繁，请一小时后再试")

    async def event_stream(db: AsyncSession):
        case = await _get_accessible_case(case_id, current_user, db)
        async for event in run_doc_pipeline_stream(
            db,
            case,
            current_user,
            doc_type=data.doc_type,
            case_facts=data.case_facts,
            extra_instructions=data.extra_instructions,
            skip_research=data.skip_research,
            research_report_ids=data.research_report_ids,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        wrap_stream_with_db(event_stream)(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{case_id}/agent/ask", response_model=CaseAgentAskOut)
async def ask_case_agent(
    case_id: int,
    data: CaseAgentAskIn,
    chain_score: int | None = Query(None, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """就当前案件向维权助手提问（基于材料状态 + 可选 LLM）。"""
    from app.core.security import check_rate_limit
    from app.services.llm_resolver import resolve_user_llm
    from app.services.orchestrator.ask import answer_case_question
    from app.services.orchestrator.gather import build_case_work_context

    if not check_rate_limit(f"case_agent_ask:{current_user.id}", max_requests=40, window_seconds=3600):
        raise HTTPException(429, "提问过于频繁，请稍后再试")

    case = await _get_accessible_case(case_id, current_user, db)
    ctx = await build_case_work_context(
        db,
        case,
        user_id=current_user.id,
        chain_completeness_score=chain_score,
    )

    llm = None
    try:
        llm = await resolve_user_llm(db, current_user)
    except Exception:
        llm = None

    result = await answer_case_question(ctx, data.question, llm=llm)
    from app.services.orchestrator.snapshot import merge_snapshot

    merge_snapshot(
        case,
        {
            "last_ask": {
                "question": data.question[:200],
                "answer": result["answer"][:500],
                "suggested_route": result["suggested_route"],
                "used_llm": bool(result.get("used_llm")),
            },
        },
    )
    await db.flush()
    return CaseAgentAskOut(
        case_id=case.id,
        answer=result["answer"],
        suggested_route=result["suggested_route"],
        suggested_label=result.get("suggested_label", ""),
        pipeline_stage=result.get("pipeline_stage", ""),
        used_llm=bool(result.get("used_llm")),
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
    """删除案件（证据及关联材料库条目一并清理；文书/报告仅解除关联）。"""
    case = await db.get(Case, case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(404, "案件不存在或无权删除")
    try:
        from app.core.db_write_lock import run_serialized_write
        from sqlalchemy import delete, update

        from app.models.contract import Contract
        from app.models.document import Document
        from app.models.research import ResearchReport
        from app.models.search import SearchRecord
        from app.services.intake.session_store import clear_case_from_intake_session
        from app.services.vault import soft_delete_materials_for_case

        async def _delete_impl() -> tuple[int, list[Evidence]]:
            settings = get_settings()
            ev_result = await db.execute(select(Evidence).where(Evidence.case_id == case_id))
            evidences = list(ev_result.scalars().all())
            evidence_ids = [e.id for e in evidences]

            for ev in evidences:
                if ev.file_path:
                    fp = settings.upload_path / ev.file_path
                    if fp.is_file():
                        fp.unlink(missing_ok=True)

            vault_removed = await soft_delete_materials_for_case(
                db,
                user_id=current_user.id,
                case_id=case_id,
                evidence_ids=evidence_ids,
            )

            # 解除关联，保留用户已生成的文书/报告/合同/检索记录
            await db.execute(
                update(Document).where(Document.case_id == case_id).values(case_id=None)
            )
            await db.execute(
                update(ResearchReport).where(ResearchReport.case_id == case_id).values(case_id=None)
            )
            await db.execute(
                update(Contract).where(Contract.case_id == case_id).values(case_id=None)
            )
            await db.execute(
                update(SearchRecord).where(SearchRecord.case_id == case_id).values(case_id=None)
            )
            await db.execute(delete(Evidence).where(Evidence.case_id == case_id))

            await clear_case_from_intake_session(db, current_user.id, case_id)
            await db.delete(case)
            await db.flush()
            return vault_removed, evidences

        vault_removed, _ = await run_serialized_write(_delete_impl)
        return {
            "message": "案件已删除",
            "id": case_id,
            "vault_materials_removed": vault_removed,
        }
    except Exception as e:
        logger.exception("Delete case failed: %s", e)
        await db.rollback()
        detail = "删除案件失败"
        if "database is locked" in str(e).lower():
            detail = "数据库繁忙，正在处理其他操作，请稍后重试"
        raise HTTPException(500, detail)


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
