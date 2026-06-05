"""文书助手流水线 — 检索争点 → 生成 → 审校 → 质量核查。"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.document import Document, Template
from app.models.research import ResearchReport
from app.models.user import User
from app.services.docgen.engine import create_engine_for_llm
from app.services.docgen.types import normalize_doc_type
from app.services.llm_resolver import resolve_user_llm
from app.services.orchestrator.gather import build_case_work_context
from app.services.orchestrator.doc_facts import build_docgen_case_facts
from app.services.orchestrator.snapshot import append_pipeline_run
from app.services.search.unified import UnifiedSearchService

logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    ("prepare", "准备案情与材料"),
    ("research", "检索法规与争点"),
    ("generate", "AI 生成文书"),
    ("review", "AI 审校润色"),
    ("quality", "质量核查"),
]


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _resolve_template(db: AsyncSession, doc_type: str) -> Template | None:
    from app.services.docgen.template_resolve import resolve_template_for_doc_type

    return await resolve_template_for_doc_type(db, doc_type)


async def _load_research_context(
    db: AsyncSession,
    *,
    owner_id: int,
    case_id: int,
    report_ids: list[int] | None,
) -> str:
    q = select(ResearchReport).where(
        ResearchReport.owner_id == owner_id,
        ResearchReport.case_id == case_id,
    )
    if report_ids:
        q = q.where(ResearchReport.id.in_(report_ids))
    q = q.order_by(ResearchReport.created_at.desc()).limit(3)
    reports = (await db.execute(q)).scalars().all()
    if not reports:
        return ""
    return "\n\n---\n\n".join(
        f"【研究报告：{r.query}】\n{(r.report or '')[:4000]}" for r in reports
    )[:8000]


async def run_doc_pipeline_stream(
    db: AsyncSession,
    case: Case,
    user: User,
    *,
    doc_type: str = "application",
    case_facts: str,
    extra_instructions: str | None = None,
    skip_research: bool = False,
    research_report_ids: list[int] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """SSE 事件：step / completed / error。"""
    run_id = uuid.uuid4().hex[:12]
    run_log: dict[str, Any] = {
        "run_id": run_id,
        "doc_type": doc_type,
        "steps": [],
        "started_at": _utc_iso(),
    }
    document_id: int | None = None
    quality_summary: str | None = None
    quality_score: int | None = None
    research_blob = ""

    try:
        llm = await resolve_user_llm(db, user)
        merged_facts = await build_docgen_case_facts(db, case, user_provided=case_facts)
        ctx = await build_case_work_context(db, case, user_id=user.id)
        cause_label = ctx.readiness.cause_label or "劳动争议"
        search_query = f"{cause_label} 劳动仲裁 {(case.title or '')[:80]}"[:200]

        for step_key, step_label in PIPELINE_STEPS:
            yield {"step": step_key, "label": step_label, "status": "running"}

            if step_key == "prepare":
                run_log["steps"].append({"id": step_key, "status": "done"})
                yield {"step": step_key, "label": step_label, "status": "done"}

            elif step_key == "research":
                prior_reports = await _load_research_context(
                    db,
                    owner_id=user.id,
                    case_id=case.id,
                    report_ids=research_report_ids,
                )
                if skip_research:
                    research_blob = prior_reports
                    run_log["steps"].append({"id": step_key, "status": "skipped"})
                    yield {"step": step_key, "label": "使用已有研究材料", "status": "done"}
                else:
                    try:
                        service = UnifiedSearchService(llm=llm)
                        result = await service.search(
                            query=search_query.strip(),
                            result_type="law",
                            top_k=5,
                        )
                        law_lines = [
                            f"- {law.title}：{(law.content or '')[:220]}"
                            for law in (result.laws or [])[:5]
                        ]
                        summary = "\n".join(law_lines)[:2500]
                        if summary:
                            research_blob = f"【法规检索摘要】\n{summary}"
                        if prior_reports:
                            research_blob = "\n\n".join(filter(None, [research_blob, prior_reports]))
                        run_log["steps"].append({"id": step_key, "status": "done", "query": search_query})
                    except Exception as e:
                        logger.warning("Pipeline research step failed: %s", e)
                        research_blob = prior_reports
                        run_log["steps"].append({"id": step_key, "status": "partial"})
                    yield {"step": step_key, "label": step_label, "status": "done"}

            elif step_key == "generate":
                template = await _resolve_template(db, doc_type)
                if not template:
                    yield {
                        "step": "error",
                        "label": "未找到文书模板",
                        "error": f"未找到类型「{doc_type}」的模板，请先在文书模板中同步",
                    }
                    return

                engine = create_engine_for_llm(llm)
                merged_extra = (extra_instructions or "").strip()
                if research_blob:
                    merged_extra = (merged_extra + "\n\n" + research_blob).strip() if merged_extra else research_blob

                try:
                    gen_result = await engine.generate(
                        case_facts=merged_facts,
                        doc_type=template.type,
                        template=template,
                        extra_instructions=merged_extra or None,
                        research_context=research_blob or None,
                    )
                except Exception as gen_exc:
                    logger.warning("Pipeline LLM generate failed, offline fallback: %s", gen_exc)
                    from app.services.docgen.offline_fallback import build_offline_structured_document
                    from app.services.docgen.structured import has_structured_renderer

                    if has_structured_renderer(template.type):
                        gen_result = build_offline_structured_document(
                            doc_type=template.type,
                            case_facts=merged_facts,
                        )
                    else:
                        raise
                doc = Document(
                    case_id=case.id,
                    template_id=template.id if template.id else None,
                    type=template.type,
                    title=gen_result.get("title", f"{template.type}文书"),
                    content=gen_result["content"],
                    ai_metadata={
                        **(gen_result.get("metadata") or {}),
                        "pipeline_run_id": run_id,
                        "generation_mode": "agent_pipeline",
                    },
                    status="generated",
                    owner_id=user.id,
                )
                db.add(doc)
                await db.flush()
                await db.refresh(doc)
                document_id = doc.id

                vault_archived = False
                try:
                    from app.services.docgen.export_archive import export_docx_and_archive

                    vault_archived = await export_docx_and_archive(
                        db, doc, user_id=user.id
                    )
                    await db.refresh(doc)
                except Exception as e:
                    logger.warning("Pipeline export/archive failed: %s", e)

                run_log["steps"].append({
                    "id": step_key,
                    "status": "done",
                    "document_id": document_id,
                    "vault_archived": vault_archived,
                })
                yield {
                    "step": step_key,
                    "label": step_label,
                    "status": "done",
                    "document_id": document_id,
                    "vault_archived": vault_archived,
                }

            elif step_key == "review":
                if not document_id:
                    run_log["steps"].append({"id": step_key, "status": "skipped"})
                    yield {"step": step_key, "label": step_label, "status": "skipped"}
                    continue
                try:
                    doc = await db.get(Document, document_id)
                    if doc:
                        engine = create_engine_for_llm(llm)
                        doc.content = await engine.review(doc.content, doc.type)
                        doc.status = "reviewed"
                        await db.flush()
                    run_log["steps"].append({"id": step_key, "status": "done"})
                except Exception as e:
                    logger.warning("Pipeline review step failed: %s", e)
                    run_log["steps"].append({"id": step_key, "status": "partial", "error": str(e)[:120]})
                yield {"step": step_key, "label": step_label, "status": "done"}

            elif step_key == "quality":
                if not document_id:
                    run_log["steps"].append({"id": step_key, "status": "skipped"})
                    yield {"step": step_key, "label": step_label, "status": "skipped"}
                    continue
                try:
                    doc = await db.get(Document, document_id)
                    if doc:
                        engine = create_engine_for_llm(llm)
                        parsed = None
                        if isinstance(doc.ai_metadata, dict):
                            parsed = doc.ai_metadata.get("parsed_case")
                        check = await engine.quality_check(doc.content, doc.type, parsed)
                        quality_score = int(check.get("quality_score") or 0)
                        quality_summary = str(check.get("summary") or "")[:500]
                        run_log["quality_check"] = {
                            "passed": check.get("passed"),
                            "quality_score": quality_score,
                            "summary": quality_summary,
                        }
                    run_log["steps"].append({"id": step_key, "status": "done"})
                except Exception as e:
                    logger.warning("Pipeline quality step failed: %s", e)
                    run_log["steps"].append({"id": step_key, "status": "partial", "error": str(e)[:120]})
                yield {
                    "step": step_key,
                    "label": step_label,
                    "status": "done",
                    "quality_score": quality_score,
                }

        run_log["completed_at"] = _utc_iso()
        run_log["document_id"] = document_id
        append_pipeline_run(case, run_log)
        await db.flush()

        vault_archived = False
        for step in run_log.get("steps") or []:
            if step.get("id") == "generate" and step.get("vault_archived"):
                vault_archived = True
                break

        yield {
            "step": "completed",
            "label": "流水线完成",
            "document_id": document_id,
            "run_id": run_id,
            "quality_score": quality_score,
            "quality_summary": quality_summary,
            "vault_archived": vault_archived,
        }
    except Exception as e:
        logger.exception("Doc pipeline failed: %s", e)
        run_log["error"] = str(e)[:300]
        run_log["completed_at"] = _utc_iso()
        append_pipeline_run(case, run_log)
        try:
            await db.flush()
        except Exception:
            pass
        if document_id:
            yield {
                "step": "completed",
                "label": "文书已生成（后续步骤未完成）",
                "document_id": document_id,
                "quality_score": quality_score,
                "quality_summary": quality_summary,
            }
        else:
            yield {"step": "error", "label": "流水线失败", "error": "文书流水线执行失败，请稍后重试"}
