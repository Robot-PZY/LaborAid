"""文书生成编排 — 短 DB 读 → LLM（无 DB）→ 串行写库。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.db_write_lock import run_serialized_write
from app.models.case import Case
from app.models.document import Document
from app.models.research import ResearchReport
from app.models.user import User
from app.schemas.document import DocumentGenerate, DocumentOut
from app.services.docgen.engine import DocumentGenerationEngine
from app.services.docgen.offline_fallback import build_offline_structured_document
from app.services.docgen.prompts import DOC_TYPE_NAMES
from app.services.docgen.structured import has_structured_renderer
from app.services.docgen.title_format import format_case_document_title
from app.services.docgen.types import normalize_doc_type
from app.services.docgen.export_archive import export_docx_and_archive
from app.services.llm_resolver import resolve_user_llm

logger = logging.getLogger(__name__)

LLM_GENERATE_TIMEOUT_SEC = 45
SAVE_RETRY_ATTEMPTS = 6


@dataclass
class GenerationPrepared:
    canonical_type: str
    template_id: int
    research_context: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    template_name: str
    template_ai_prompt: str
    template_structure: dict
    case_title: str | None = None


async def _prepare_generation(
    db: AsyncSession,
    current_user: User,
    data: DocumentGenerate,
) -> GenerationPrepared:
    from app.services.docgen.template_resolve import resolve_template_for_doc_type

    canonical_type = normalize_doc_type(data.type) or data.type
    template = await resolve_template_for_doc_type(
        db,
        canonical_type,
        template_id=data.template_id,
        owner_id=current_user.id,
    )
    if template and data.template_id:
        if not template.is_public and template.owner_id != current_user.id:
            raise PermissionError("无权使用该模板")
    if not template:
        raise ValueError(f"未找到类型为「{canonical_type}」的文书模板")

    llm = await resolve_user_llm(db, current_user)

    research_context = ""
    if data.research_report_ids:
        rr_result = await db.execute(
            select(ResearchReport).where(
                ResearchReport.id.in_(data.research_report_ids),
                ResearchReport.owner_id == current_user.id,
            )
        )
        reports = rr_result.scalars().all()
        if reports:
            research_context = "\n\n---\n\n".join(
                f"【研究报告：{r.query}】\n{r.report[:4000]}"
                for r in reports
            )[:8000]

    case_title: str | None = None
    if data.case_id:
        case_row = await db.get(Case, data.case_id)
        if case_row and case_row.owner_id == current_user.id:
            case_title = case_row.title

    # 始终使用用户选择的文书类型，不应用模板的 type 覆盖
    return GenerationPrepared(
        canonical_type=canonical_type,
        template_id=template.id,
        research_context=research_context,
        llm_base_url=llm.base_url,
        llm_api_key=llm.api_key,
        llm_model=llm.model,
        template_name=template.name,
        template_ai_prompt=template.ai_prompt,
        template_structure=template.structure if isinstance(template.structure, dict) else {},
        case_title=case_title,
    )


def _template_proxy(prepared: GenerationPrepared):
    return SimpleNamespace(
        id=prepared.template_id,
        type=prepared.canonical_type,
        name=prepared.template_name,
        ai_prompt=prepared.template_ai_prompt,
        structure=prepared.template_structure,
    )


def _apply_case_title(gen_result: dict, prepared: GenerationPrepared) -> dict:
    """统一为生成结果加上「案件名-文书名」标题。"""
    doc_label = DOC_TYPE_NAMES.get(prepared.canonical_type, prepared.canonical_type)
    parsed = (gen_result.get("metadata") or {}).get("parsed_case") or {}
    parties = parsed.get("parties") or {}
    plaintiff = (parties.get("plaintiff") or {}).get("name", "")
    defendant = (parties.get("defendant") or {}).get("name", "")
    gen_result = dict(gen_result)
    gen_result["title"] = format_case_document_title(
        case_title=prepared.case_title,
        doc_type_label=doc_label,
        plaintiff=plaintiff,
        defendant=defendant,
    )
    return gen_result


async def _run_engine_generate(
    prepared: GenerationPrepared,
    data: DocumentGenerate,
) -> dict:
    settings = get_settings()
    engine = DocumentGenerationEngine(
        settings,
        llm_base_url=prepared.llm_base_url,
        llm_api_key=prepared.llm_api_key,
        llm_model=prepared.llm_model,
    )
    return await engine.generate(
        case_facts=data.case_facts,
        doc_type=prepared.canonical_type,
        template=_template_proxy(prepared),
        extra_instructions=data.extra_instructions,
        research_context=prepared.research_context or None,
    )


async def _resolve_generation_content(
    prepared: GenerationPrepared,
    data: DocumentGenerate,
) -> dict:
    """优先 LLM 生成；超时或失败则规则模板兜底。"""
    baseline: dict
    if has_structured_renderer(prepared.canonical_type):
        baseline = build_offline_structured_document(
            doc_type=prepared.canonical_type,
            case_facts=data.case_facts,
            case_title=prepared.case_title,
        )
    else:
        label = DOC_TYPE_NAMES.get(prepared.canonical_type, prepared.canonical_type)
        baseline = {
            "title": format_case_document_title(
                case_title=prepared.case_title,
                doc_type_label=label,
            ),
            "content": f"# {label}\n\n{data.case_facts}\n",
            "metadata": {"generation_mode": "plain"},
        }

    try:
        ai_result = await asyncio.wait_for(
            _run_engine_generate(prepared, data),
            timeout=LLM_GENERATE_TIMEOUT_SEC,
        )
        content = (ai_result.get("content") or "").strip()
        if content and len(content) >= max(200, len(baseline.get("content", "")) // 2):
            merged_meta = {
                **baseline.get("metadata", {}),
                **(ai_result.get("metadata") or {}),
                "generation_mode": "llm",
            }
            ai_result = {**ai_result, "metadata": merged_meta}
            return _apply_case_title(ai_result, prepared)
    except Exception as exc:
        logger.warning("LLM document generate fallback to offline: %s", exc)

    return _apply_case_title(baseline, prepared)


async def _persist_document(
    *,
    current_user: User,
    data: DocumentGenerate,
    prepared: GenerationPrepared,
    gen_result: dict,
) -> DocumentOut:
    """串行写库：先保存文书记录，再尝试导出 Word / 材料库。"""

    async def _save_once() -> Document:
        async with AsyncSessionLocal() as save_db:
            doc = Document(
                case_id=data.case_id,
                template_id=prepared.template_id,
                type=prepared.canonical_type,
                title=data.title or gen_result.get("title", f"{prepared.canonical_type}文书"),
                content=gen_result["content"],
                ai_metadata=gen_result.get("metadata", {}),
                status="generated",
                owner_id=current_user.id,
            )
            save_db.add(doc)
            await save_db.flush()
            await save_db.refresh(doc)
            await save_db.commit()
            return doc

    doc: Document | None = None
    last_exc: Exception | None = None
    for attempt in range(SAVE_RETRY_ATTEMPTS):
        try:
            doc = await run_serialized_write(_save_once)
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("Save document retry %s/%s: %s", attempt + 1, SAVE_RETRY_ATTEMPTS, exc)
            await asyncio.sleep(0.5 * (attempt + 1))
    if doc is None:
        if last_exc:
            raise last_exc
        raise RuntimeError("文书保存失败")

    archived = False
    try:

        async def _export_once() -> bool:
            async with AsyncSessionLocal() as export_db:
                row = await export_db.get(Document, doc.id)
                if not row:
                    return False
                ok = await export_docx_and_archive(export_db, row, user_id=current_user.id)
                await export_db.commit()
                return ok

        archived = await run_serialized_write(_export_once)
    except Exception as exc:
        logger.warning("Export/archive after generate failed for doc %s: %s", doc.id, exc)

    return DocumentOut.model_validate(doc).model_copy(update={"vault_archived": archived})


async def generate_document_result(
    current_user: User,
    data: DocumentGenerate,
) -> DocumentOut:
    async with AsyncSessionLocal() as prep_db:
        prepared = await _prepare_generation(prep_db, current_user, data)

    gen_result = await _resolve_generation_content(prepared, data)
    return await _persist_document(
        current_user=current_user,
        data=data,
        prepared=prepared,
        gen_result=gen_result,
    )
