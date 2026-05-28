"""证据管理路由"""

import asyncio
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, validate_upload
from app.config import get_settings
from app.models.user import User
from app.models.case import Case
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceOut
from app.services.evidence.ocr import extract_text
from app.services.evidence.analysis import analyze_evidence
from app.services.evidence.chain import analyze_evidence_chain, generate_cross_examination
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm
from app.services.ocr_status import classify_ocr_result

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_evidence_out(row: Evidence, *, truncate_ocr: bool = False) -> EvidenceOut:
    out = EvidenceOut.model_validate(row)
    out.has_file = row.file_path is not None
    if truncate_ocr and out.ocr_text and len(out.ocr_text) > 300:
        out.ocr_text = out.ocr_text[:300] + "..."
    status, msg = classify_ocr_result(row.ocr_text, has_file=out.has_file)
    out.ocr_status = status
    out.ocr_message = msg
    return out

ALLOWED_EVIDENCE_TYPES = {
    "documentary", "physical", "electronic", "testimony", "audio_visual", "expert",
}


@router.get("", response_model=list[EvidenceOut])
async def list_evidence(
    case_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(max(limit, 1), 100)
    try:
        base_where = Case.owner_id == current_user.id
        # Count query
        count_q = select(func.count(Evidence.id)).join(Case).where(base_where)
        if case_id:
            count_q = count_q.where(Evidence.case_id == case_id)
        total = (await db.execute(count_q)).scalar() or 0

        query = select(Evidence).join(Case).where(base_where)
        if case_id:
            query = query.where(Evidence.case_id == case_id)
        query = query.order_by(Evidence.sort_order, Evidence.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = []
        for e in result.scalars().all():
            out = _build_evidence_out(e, truncate_ocr=True)
            if out.analysis and len(out.analysis) > 300:
                out.analysis = out.analysis[:300] + "..."
            items.append(out)
        return JSONResponse(
            content=[i.model_dump(mode="json") for i in items],
            headers={"X-Total-Count": str(total)},
        )
    except Exception as e:
        logger.error("List evidence failed: %s", e)
        raise HTTPException(500, "查询证据列表失败")


@router.post("", response_model=EvidenceOut, status_code=201)
async def create_evidence(
    data: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if data.type not in ALLOWED_EVIDENCE_TYPES:
            raise HTTPException(400, f"无效的证据类型，允许值: {', '.join(sorted(ALLOWED_EVIDENCE_TYPES))}")
        # 验证案件归属
        case = await db.execute(select(Case).where(Case.id == data.case_id, Case.owner_id == current_user.id))
        if not case.scalar_one_or_none():
            raise HTTPException(404, "案件不存在")
        row = Evidence(
            case_id=data.case_id,
            type=data.type,
            title=data.title,
            tags=data.tags,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return _build_evidence_out(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create evidence failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "创建证据失败")


@router.post("/{evidence_id}/upload", response_model=EvidenceOut)
async def upload_file(
    evidence_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "证据不存在")

        # Use centralized upload validation (extension + MIME + size + injection scan)
        content = await validate_upload(file)

        settings = get_settings()
        upload_dir = settings.upload_path / "evidence" / str(row.case_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename or ".bin").suffix
        safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
        dest = upload_dir / safe_name
        await asyncio.to_thread(dest.write_bytes, content)

        row.file_path = f"evidence/{row.case_id}/{safe_name}"
        await db.commit()
        await db.refresh(row)

        # 自动OCR
        try:
            vision = await resolve_vision_llm(db, current_user)
            ocr_text = await extract_text(dest, vision_llm=vision)
            row.ocr_text = ocr_text
            await db.commit()
            await db.refresh(row)
        except Exception as e:
            logger.warning("Auto OCR failed for evidence %d: %s", evidence_id, e)
            row.ocr_text = f"[文字提取失败: {e}]"
            await db.commit()
            await db.refresh(row)

        vault_archived = False
        try:
            from app.services.vault import archive_file_to_vault

            vault_row = await archive_file_to_vault(
                db,
                user_id=current_user.id,
                content=content,
                original_filename=file.filename or safe_name,
                source="evidence",
                source_id=row.id,
                case_id=row.case_id,
                mime_type=file.content_type,
            )
            vault_archived = vault_row is not None
        except Exception as e:
            logger.warning("Vault archive from evidence %d failed: %s", evidence_id, e)

        out = _build_evidence_out(row)
        out.vault_archived = vault_archived
        return out
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload evidence file failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "上传证据文件失败")


def _infer_evidence_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}:
        return "audio_visual"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}:
        return "electronic"
    return "documentary"


@router.post("/quick-upload", response_model=EvidenceOut, status_code=201)
async def quick_upload_for_case(
    case_id: int = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    evidence_type: str = Form("electronic"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建证据记录并上传文件（一步完成），同步归档到材料库。"""
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        evidence_type = _infer_evidence_type(file.filename or "")
    case = await db.execute(
        select(Case).where(Case.id == case_id, Case.owner_id == current_user.id)
    )
    if not case.scalar_one_or_none():
        raise HTTPException(404, "案件不存在")

    fname = file.filename or "未命名文件"
    row = Evidence(
        case_id=case_id,
        type=evidence_type,
        title=(title or Path(fname).stem or fname).strip()[:500],
        tags=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return await upload_file(row.id, file, db, current_user)


@router.get("/{evidence_id}", response_model=EvidenceOut)
async def get_evidence(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "证据不存在")
    return _build_evidence_out(row)


@router.put("/{evidence_id}", response_model=EvidenceOut)
async def update_evidence(
    evidence_id: int,
    data: EvidenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "证据不存在")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await db.commit()
        await db.refresh(row)
        return _build_evidence_out(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update evidence failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "更新证据失败")


@router.delete("/{evidence_id}")
async def delete_evidence(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "证据不存在")
        if row.file_path:
            settings = get_settings()
            fp = settings.upload_path / row.file_path
            if fp.exists():
                fp.unlink()
        try:
            from app.services.vault import mark_vault_source_deleted

            await mark_vault_source_deleted(
                db,
                user_id=current_user.id,
                source="evidence",
                source_id=row.id,
            )
        except Exception as e:
            logger.warning("Vault cleanup for evidence %d failed: %s", evidence_id, e)
        await db.delete(row)
        await db.commit()
        return {"message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete evidence failed: %s", e)
        await db.rollback()
        raise HTTPException(500, "删除证据失败")


@router.post("/{evidence_id}/analyze", response_model=EvidenceOut)
async def analyze_evidence_endpoint(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "证据不存在")

        # 如果有文件但还没OCR，先提取文字
        if row.file_path and not row.ocr_text:
            settings = get_settings()
            fp = settings.upload_path / row.file_path
            if fp.exists():
                vision = await resolve_vision_llm(db, current_user)
                row.ocr_text = await extract_text(fp, vision_llm=vision)
                await db.commit()
                await db.refresh(row)

        # 获取案件背景
        case_result = await db.execute(select(Case).where(Case.id == row.case_id))
        case = case_result.scalar_one_or_none()
        case_context = case.description if case else ""

        import time
        start = time.time()
        llm = await resolve_user_llm(db, current_user)
        row.analysis = await analyze_evidence(row.ocr_text or "", case_context, llm=llm)
        logger.info("Evidence analysis took %.2fs for evidence %d", time.time() - start, evidence_id)
        await db.commit()
        await db.refresh(row)

        return _build_evidence_out(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analyze evidence failed: %s", e)
        raise HTTPException(500, "证据分析失败，请稍后重试")


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row or not row.file_path:
        raise HTTPException(404, "文件不存在")

    settings = get_settings()
    fp = settings.upload_path / row.file_path
    if not fp.exists():
        raise HTTPException(404, "文件已被删除")

    return FileResponse(str(fp), filename=fp.name, media_type="application/octet-stream")


@router.post("/chain-analysis/{case_id}")
async def chain_analysis(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析案件的证据链完整性"""
    try:
        case_result = await db.execute(
            select(Case).where(Case.id == case_id, Case.owner_id == current_user.id)
        )
        case = case_result.scalar_one_or_none()
        if not case:
            raise HTTPException(404, "案件不存在")

        ev_result = await db.execute(
            select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.sort_order)
        )
        evidence_list = []
        for ev in ev_result.scalars().all():
            evidence_list.append({
                "id": ev.id,
                "title": ev.title,
                "type": ev.type,
                "ocr_text": ev.ocr_text,
                "analysis": ev.analysis,
                "tags": ev.tags,
            })

        if not evidence_list:
            raise HTTPException(400, "该案件暂无证据，无法进行证据链分析")

        llm = await resolve_user_llm(db, current_user)
        result = await analyze_evidence_chain(case.description or case.title, evidence_list, llm=llm)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chain analysis failed: %s", e)
        raise HTTPException(500, "证据链分析失败，请稍后重试")


@router.post("/{evidence_id}/cross-examination")
async def cross_examination(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为证据生成质证意见"""
    try:
        result = await db.execute(
            select(Evidence).join(Case).where(Evidence.id == evidence_id, Case.owner_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(404, "证据不存在")

        if not row.ocr_text:
            raise HTTPException(400, "证据文字为空，请先上传文件并完成OCR")

        case_result = await db.execute(select(Case).where(Case.id == row.case_id))
        case = case_result.scalar_one_or_none()
        case_context = f"{case.description or ''} {case.title or ''}" if case else ""

        llm = await resolve_user_llm(db, current_user)
        opinion = await generate_cross_examination(
            evidence_text=row.ocr_text,
            evidence_type=row.type,
            case_context=case_context,
            llm=llm,
        )
        return {"cross_examination": opinion}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cross examination failed: %s", e)
        raise HTTPException(500, "质证意见生成失败，请稍后重试")
