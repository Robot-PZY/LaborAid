import asyncio
import json
import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, validate_upload, sanitize_filename, check_rate_limit
from app.config import get_settings
from app.models.user import User
from app.models.document import Document, Template
from app.schemas.document import (
    DocumentBatchDelete,
    DocumentGenerate,
    DocumentUpdate,
    DocumentOut,
    DocumentExport,
    DocumentBundleGenerate,
)
from app.services.docgen.engine import create_engine_for_llm
from app.services.docgen.types import normalize_doc_type
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm
from app.services.evidence.ocr import extract_text

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_CONTENT_LENGTH = 200000


async def _finalize_generated_doc(
    db: AsyncSession,
    doc: Document,
    *,
    user_id: int,
) -> DocumentOut:
    """生成 Word 副本、写入材料库，并返回带 vault_archived 标记的响应。"""
    from app.services.docgen.export_archive import export_docx_and_archive

    archived = await export_docx_and_archive(db, doc, user_id=user_id)
    await db.refresh(doc)
    return DocumentOut.model_validate(doc).model_copy(update={"vault_archived": archived})


# ---------------------------------------------------------------------------
# Quality check response schema
# ---------------------------------------------------------------------------

class QualityCheckIssue(BaseModel):
    """A single quality check issue."""
    category: str = ""
    severity: str = "info"  # error / warning / info
    description: str = ""
    location: str = ""
    suggestion: str = ""


class QualityCheckResponse(BaseModel):
    """Structured response for document quality check."""
    document_id: int
    quality_check: dict  # Contains: passed, issues, checks, quality_score, summary



@router.post("/extract-text")
async def extract_text_from_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文件并提取文字内容，供文书生成和法律研究使用。"""
    content = await validate_upload(file)

    settings = get_settings()
    tmp_dir = settings.upload_path / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or ".bin").suffix
    tmp_path = tmp_dir / f"{uuid.uuid4().hex[:12]}{ext}"

    try:
        await asyncio.to_thread(tmp_path.write_bytes, content)
        vision = await resolve_vision_llm(db, current_user)
        text = await extract_text(tmp_path, vision_llm=vision)
    finally:
        await asyncio.to_thread(tmp_path.unlink, missing_ok=True)

    return {"filename": sanitize_filename(file.filename or ""), "text": text}


class DocumentPreviewRequest(BaseModel):
    content: str = ""
    title: str | None = None


class DocumentPreviewResponse(BaseModel):
    html: str
    css: str


@router.post("/preview/render", response_model=DocumentPreviewResponse)
async def render_document_preview(
    data: DocumentPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """将 Markdown 渲染为与 Word/HTML 导出一致的法院标准 HTML（供前端预览）。"""
    from app.services.docgen.court_markdown import build_preview_html
    from app.services.docgen.court_document_styles import COURT_DOCUMENT_CSS

    content = (data.content or "")[:MAX_CONTENT_LENGTH]
    html = build_preview_html(content, title=data.title)
    return DocumentPreviewResponse(html=html, css=COURT_DOCUMENT_CSS)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    case_id: int | None = None,
    type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    base_filter = Document.owner_id == current_user.id
    # Count query
    count_q = select(func.count(Document.id)).where(base_filter)
    if case_id:
        count_q = count_q.where(Document.case_id == case_id)
    if type:
        count_q = count_q.where(Document.type == type)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(Document).where(base_filter)
    if case_id:
        q = q.where(Document.case_id == case_id)
    if type:
        q = q.where(Document.type == type)
    q = q.order_by(Document.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()

    # Truncate content in list view
    response_data = []
    for doc in items:
        out = DocumentOut.model_validate(doc)
        if out.content and len(out.content) > 500:
            out.content = out.content[:500] + "..."
        response_data.append(out)

    return JSONResponse(
        content=[r.model_dump(mode="json") for r in response_data],
        headers={"X-Total-Count": str(total)},
    )


@router.post("/generate", response_model=DocumentOut, status_code=201)
async def generate_document(
    data: DocumentGenerate,
    current_user: User = Depends(get_current_user),
):
    # Rate limit document generation: 10 per hour per user
    if not check_rate_limit(f"doc_gen:{current_user.id}", max_requests=10, window_seconds=3600):
        raise HTTPException(429, "文书生成请求过于频繁，请一小时后再试")

    if data.case_facts and len(data.case_facts) > MAX_CONTENT_LENGTH:
        raise HTTPException(400, f"案件事实内容不能超过 {MAX_CONTENT_LENGTH} 个字符")

    from app.services.docgen.generate_service import generate_document_result

    try:
        return await generate_document_result(current_user, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, "文书生成服务暂时不可用，请稍后重试") from exc
    except Exception as exc:
        logger.exception("Document generation failed: %s", exc)
        msg = str(exc).lower()
        if "locked" in msg:
            detail = "数据库繁忙，请关闭多余后端窗口后重试（或运行 stop-laboraid.bat 再启动）"
        else:
            detail = "文书生成失败，请稍后重试"
        raise HTTPException(500, detail) from exc


@router.post("/generate-stream")
async def generate_document_stream(
    data: DocumentGenerate,
    current_user: User = Depends(get_current_user),
):
    """SSE endpoint that streams document generation progress steps."""
    import time as _time

    from app.core.streaming_db import wrap_stream_with_db

    if not check_rate_limit(f"doc_gen:{current_user.id}", max_requests=10, window_seconds=3600):
        raise HTTPException(429, "文书生成请求过于频繁，请一小时后再试")

    canonical_type = normalize_doc_type(data.type) or data.type

    STEPS = [
        ("parsing", "解析案件信息"),
        ("searching", "检索相关法规"),
        ("extracting", "提取法律要点"),
        ("matching", "匹配文书模板"),
        ("generating", "AI生成文书"),
        ("checking", "质量检查"),
        ("reviewing", "最终审查"),
    ]

    async def event_stream(db: AsyncSession):
        start = _time.monotonic()
        resolved_type = canonical_type
        try:
            from app.services.docgen.template_resolve import resolve_template_for_doc_type

            template = await resolve_template_for_doc_type(
                db,
                resolved_type,
                template_id=data.template_id,
                owner_id=current_user.id,
            )
            if template:
                resolved_type = template.type

            if not template:
                yield f"data: {json.dumps({'step': 'error', 'label': '未找到模板', 'error': '未找到对应文书模板，请先在模板库同步'}, ensure_ascii=False)}\n\n"
                return

            research_context = ""
            if data.research_report_ids:
                from app.models.research import ResearchReport

                rr_result = await db.execute(
                    select(ResearchReport).where(
                        ResearchReport.id.in_(data.research_report_ids),
                        ResearchReport.owner_id == current_user.id,
                    )
                )
                reports = rr_result.scalars().all()
                if reports:
                    research_context = "\n\n---\n\n".join(
                        f"【研究报告：{r.query}】\n{r.report[:4000]}" for r in reports
                    )[:8000]

            llm = await resolve_user_llm(db, current_user)
            stream_engine = create_engine_for_llm(llm)

            for step_key, step_label in STEPS:
                elapsed = round(_time.monotonic() - start, 1)
                yield f"data: {json.dumps({'step': step_key, 'label': step_label, 'elapsed': elapsed}, ensure_ascii=False)}\n\n"

            gen_result = await stream_engine.generate(
                case_facts=data.case_facts,
                doc_type=resolved_type,
                template=template,
                extra_instructions=data.extra_instructions,
                research_context=research_context or None,
            )

            doc = Document(
                case_id=data.case_id,
                template_id=template.id,
                type=resolved_type,
                title=data.title or gen_result.get("title", f"{resolved_type}文书"),
                content=gen_result["content"],
                ai_metadata=gen_result.get("metadata", {}),
                status="generated",
                owner_id=current_user.id,
            )
            db.add(doc)
            await db.flush()
            await db.refresh(doc)

            from app.services.docgen.export_archive import export_docx_and_archive

            vault_archived = await export_docx_and_archive(db, doc, user_id=current_user.id)
            await db.refresh(doc)

            elapsed = round(_time.monotonic() - start, 1)
            yield f"data: {json.dumps({'step': 'completed', 'label': '生成完成', 'elapsed': elapsed, 'document_id': doc.id, 'vault_archived': vault_archived}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("SSE document generation failed: %s", e)
            yield f"data: {json.dumps({'step': 'error', 'label': '生成失败', 'error': '文书生成失败，请稍后重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        wrap_stream_with_db(event_stream)(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-bundle")
async def generate_document_bundle(
    data: DocumentBundleGenerate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多文书集合生成 — 一次性生成多份关联文书并确保一致性。

    支持预设（preset）或自定义文书类型列表（doc_types）。
    """
    from app.services.docgen.prompts import BUNDLE_PRESETS

    # 验证参数
    if not data.preset and not data.doc_types:
        raise HTTPException(400, "请指定 preset（预设名称）或 doc_types（文书类型列表）")

    if data.preset and data.preset not in BUNDLE_PRESETS:
        available = ", ".join(BUNDLE_PRESETS.keys())
        raise HTTPException(400, f"未知预设 '{data.preset}'，可用预设: {available}")

    # 查询研究报告作为生成依据
    research_context = ""
    if data.research_report_ids:
        from app.models.research import ResearchReport
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

    # 调用引擎生成集合
    llm = await resolve_user_llm(db, current_user)
    engine = create_engine_for_llm(llm)
    try:
        bundle_result = await engine.generate_bundle(
            case_facts=data.case_facts,
            doc_types=data.doc_types or [],
            preset=data.preset,
            extra_instructions=data.extra_instructions,
            research_context=research_context or None,
        )
    except RuntimeError as e:
        raise HTTPException(503, "文书集合生成服务暂时不可用，请稍后重试")
    except Exception as e:
        logger.exception("Bundle generation failed: %s", e)
        raise HTTPException(500, "文书集合生成失败，请稍后重试")

    # 保存所有文书到数据库
    saved_docs = []
    for doc_data in bundle_result.get("documents", []):
        doc = Document(
            case_id=data.case_id,
            type=doc_data["doc_type"],
            title=doc_data.get("title", doc_data["doc_type"]),
            content=doc_data.get("content", ""),
            ai_metadata=doc_data.get("metadata", {}),
            status="generated",
            owner_id=current_user.id,
        )
        db.add(doc)
        saved_docs.append(doc)

    await db.flush()
    for doc in saved_docs:
        await db.refresh(doc)

    return {
        "documents": [
            {
                "id": doc.id,
                "type": doc.type,
                "title": doc.title,
                "status": doc.status,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in saved_docs
        ],
        "consistency_check": bundle_result.get("consistency_check", {}),
        "total": len(saved_docs),
    }


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")
    return doc


async def _get_owned_document(doc_id: int, current_user: User, db: AsyncSession) -> Document:
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")
    return doc


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文书及关联导出文件（content、ai_metadata 等随记录一并删除）。"""
    doc = await _get_owned_document(doc_id, current_user, db)
    settings = get_settings()
    try:
        from app.services.docgen.document_cleanup import cleanup_document_files

        removed_files = await cleanup_document_files(
            doc.id,
            exported_path=doc.exported_path,
            uploads_root=settings.upload_path,
        )
        try:
            from app.services.vault import mark_vault_source_deleted

            await mark_vault_source_deleted(
                db,
                user_id=current_user.id,
                source="document",
                source_id=doc.id,
            )
        except Exception as e:
            logger.warning("Vault cleanup for document %s failed: %s", doc_id, e)
        await db.delete(doc)
        await db.flush()
        return {"message": "文书已删除", "id": doc_id, "files_removed": removed_files}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Delete document %s failed: %s", doc_id, e)
        await db.rollback()
        raise HTTPException(500, "删除文书失败")


@router.post("/batch-delete")
async def batch_delete_documents(
    data: DocumentBatchDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量删除当前用户的文书。"""
    if not data.ids:
        return {"message": "未选择文书", "deleted_count": 0, "not_found_count": 0, "files_removed": 0}

    unique_ids = list(dict.fromkeys(data.ids))[:100]
    settings = get_settings()
    from app.services.docgen.document_cleanup import cleanup_document_files

    result = await db.execute(
        select(Document).where(
            Document.id.in_(unique_ids),
            Document.owner_id == current_user.id,
        )
    )
    rows = result.scalars().all()
    found_ids = {r.id for r in rows}
    files_removed = 0
    try:
        for doc in rows:
            files_removed += await cleanup_document_files(
                doc.id,
                exported_path=doc.exported_path,
                uploads_root=settings.upload_path,
            )
            await db.delete(doc)
        await db.flush()
        return {
            "message": "批量删除完成",
            "deleted_count": len(rows),
            "not_found_count": len(unique_ids) - len(rows),
            "files_removed": files_removed,
            "deleted_ids": list(found_ids),
        }
    except Exception as e:
        logger.exception("Batch delete documents failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "批量删除文书失败")


@router.put("/{doc_id}", response_model=DocumentOut)
async def update_document(
    doc_id: int,
    data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_document(doc_id, current_user, db)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(doc, k, v)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/{doc_id}/export")
async def export_document(
    doc_id: int,
    data: DocumentExport,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")

    settings = get_settings()
    output_dir = settings.upload_path / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    if data.format == "docx":
        from app.services.docgen.export_archive import export_docx_and_archive

        archived = await export_docx_and_archive(db, doc, user_id=current_user.id)
        await db.refresh(doc)
        if doc.exported_path:
            filepath = settings.upload_path / doc.exported_path
        else:
            from app.services.docgen.word_export import export_to_docx

            filepath = Path(await export_to_docx(doc, output_dir))
        if not filepath.is_file():
            raise HTTPException(500, "Word 导出失败")
        download_name = Path(filepath).name
        return FileResponse(
            str(filepath),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
            headers={"X-Vault-Archived": "1" if archived else "0"},
        )
    elif data.format == "html":
        from app.services.docgen.html_export import export_to_html
        filepath = await export_to_html(doc, output_dir)
        return FileResponse(
            filepath,
            media_type="text/html",
            filename=Path(filepath).name,
        )
    elif data.format == "pdf":
        try:
            from app.services.docgen.pdf_export import export_to_pdf
            filepath = await export_to_pdf(doc, output_dir)
            return FileResponse(
                filepath,
                media_type="application/pdf",
                filename=Path(filepath).name,
            )
        except RuntimeError as e:
            raise HTTPException(400, str(e))
    elif data.format == "markdown":
        filepath = output_dir / f"{doc.id}_{doc.title}.md"
        await asyncio.to_thread(filepath.write_text, doc.content, "utf-8")
        return FileResponse(
            filepath,
            media_type="text/markdown",
            filename=filepath.name,
        )
    else:
        raise HTTPException(400, f"不支持的导出格式: {data.format}")


@router.post("/{doc_id}/review", response_model=DocumentOut)
async def review_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")

    llm = await resolve_user_llm(db, current_user)
    engine = create_engine_for_llm(llm)
    try:
        reviewed_content = await engine.review(doc.content, doc.type)
    except RuntimeError as e:
        raise HTTPException(503, "文书审查服务暂时不可用，请稍后重试")
    doc.content = reviewed_content
    doc.status = "reviewed"
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/{doc_id}/verify-laws")
async def verify_document_laws(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """法条核查 — 多源交叉验证文书中引用的法条准确性"""
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")

    llm = await resolve_user_llm(db, current_user)
    engine = create_engine_for_llm(llm)
    results = await engine.verify_laws_in_content(doc.content)
    return {"document_id": doc_id, "verification_results": results, "total": len(results)}


@router.post("/{doc_id}/quality-check", response_model=QualityCheckResponse)
async def quality_check_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """文书质量核查 — 自动化验证文书质量（法条、金额、逻辑、格式、要素完整性）"""
    doc = await db.get(Document, doc_id)
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(404, "文书不存在")

    llm = await resolve_user_llm(db, current_user)
    engine = create_engine_for_llm(llm)
    parsed_case = None
    if doc.ai_metadata and isinstance(doc.ai_metadata, dict):
        parsed_case = doc.ai_metadata.get("parsed_case")

    try:
        check_result = await engine.quality_check(doc.content, doc.type, parsed_case)
    except RuntimeError as e:
        raise HTTPException(503, "质量核查服务暂时不可用，请稍后重试")
    except Exception as e:
        logger.exception("Quality check failed: %s", e)
        raise HTTPException(500, "质量核查失败，请稍后重试")

    return QualityCheckResponse(document_id=doc_id, quality_check=check_result)
