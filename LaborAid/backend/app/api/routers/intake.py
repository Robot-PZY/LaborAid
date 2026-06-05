"""维权前台 API — 案情分析与建案。"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, validate_upload
from app.models.user import User
from app.models.case import Case
from app.schemas.intake import (
    IntakeAnalyzeResponse,
    IntakeCreateCaseRequest,
    IntakeSessionSaveRequest,
    IntakeSessionStoredOut,
    IntakeStructuredRequest,
)
from app.services.intake.session_store import (
    analyzer_result_to_session,
    delete_user_intake_session,
    get_user_intake_session,
    session_has_plan,
    upsert_user_intake_session,
)
from app.services.intake.case_binding import bind_intake_to_new_case
from app.schemas.case import CaseOut
from app.services.intake.analyzer import analyze_intake
from app.services.intake.structured_builder import build_structured_intake
from app.services.llm_resolver import resolve_user_llm, resolve_vision_llm
from app.services.evidence.ocr import extract_text
from app.api.routers.cases import _case_to_out, ALLOWED_CASE_TYPES

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGES = 3
MAX_TEXT_LENGTH = 8000


@router.post("/analyze", response_model=IntakeAnalyzeResponse)
async def analyze_intake_endpoint(
    text: str = Form(""),
    images: list[UploadFile] | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """维权前台：文字 + 可选图片 → 案由识别、工具推荐、预填建议。"""
    upload_list = images or []
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(400, f"描述不能超过 {MAX_TEXT_LENGTH} 字")
    if len(upload_list) > MAX_IMAGES:
        raise HTTPException(400, f"最多上传 {MAX_IMAGES} 个文件")

    if not text.strip() and not upload_list:
        raise HTTPException(400, "请至少输入文字描述或上传一个文件")

    image_text_parts: list[str] = []
    if upload_list:
        vision = await resolve_vision_llm(db, current_user)
        for img in upload_list:
            if not img.filename:
                continue
            try:
                raw = await validate_upload(img, allowed_extensions={
                    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".pdf",
                    ".doc", ".docx", ".txt", ".md",
                })
            except HTTPException:
                raise
            suffix = Path(img.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)
            try:
                ocr = await extract_text(tmp_path, vision_llm=vision)
                if ocr and not ocr.startswith("["):
                    image_text_parts.append(f"【{img.filename}】\n{ocr[:3000]}")
            except Exception as exc:
                logger.warning("Intake OCR failed for %s: %s", img.filename, exc)
            finally:
                tmp_path.unlink(missing_ok=True)

    image_text = "\n\n".join(image_text_parts)
    llm = await resolve_user_llm(db, current_user)
    result = await analyze_intake(text, image_text, llm=llm)
    validated = IntakeAnalyzeResponse.model_validate(result)

    try:
        case_facts = "\n\n".join(filter(None, [text.strip(), validated.extracted_from_images]))
        session_payload = analyzer_result_to_session(
            validated.model_dump(mode="json"),
            input_text=text.strip(),
            case_facts=case_facts,
        )
        await upsert_user_intake_session(db, current_user.id, session_payload)
    except Exception as exc:
        logger.warning("Persist intake session after analyze failed: %s", exc)

    return validated


@router.get("/session", response_model=IntakeSessionStoredOut | None)
async def get_intake_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取当前用户已保存的维权咨询方案（重新登录后可恢复）。"""
    row = await get_user_intake_session(db, current_user.id)
    if not row or not session_has_plan(row.session_data):
        return None
    return IntakeSessionStoredOut(session=row.session_data, updated_at=row.updated_at)


@router.put("/session", response_model=IntakeSessionStoredOut)
async def save_intake_session(
    data: IntakeSessionSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存/更新维权咨询方案（步骤进度、建案 ID 等）。"""
    if not session_has_plan(data.session):
        raise HTTPException(400, "方案内容为空，无法保存")
    try:
        row = await upsert_user_intake_session(db, current_user.id, data.session)
        return IntakeSessionStoredOut(session=row.session_data, updated_at=row.updated_at)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.error("Save intake session failed: %s", exc)
        raise HTTPException(500, "保存维权方案失败") from exc


@router.delete("/session")
async def clear_intake_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """结束并删除已保存的维权咨询方案。"""
    deleted = await delete_user_intake_session(db, current_user.id)
    return {"deleted": deleted}


@router.post("/structured", response_model=IntakeAnalyzeResponse)
async def structured_intake_endpoint(
    data: IntakeStructuredRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """专项通道：结构化表单 → 维权计划（规则构建，不调用 LLM）。"""
    try:
        result = build_structured_intake(
            channel_id=data.channel_id.strip(),
            scenario_id=data.scenario_id.strip(),
            answers=data.answers or {},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.error("Structured intake failed: %s", exc)
        raise HTTPException(500, "生成维权方案失败") from exc

    validated = IntakeAnalyzeResponse.model_validate(result)
    try:
        session_payload = analyzer_result_to_session(
            validated.model_dump(mode="json"),
            input_text="",
            case_facts=validated.case_facts or validated.summary,
        )
        await upsert_user_intake_session(db, current_user.id, session_payload)
    except Exception as exc:
        logger.warning("Persist intake session after structured failed: %s", exc)

    return validated


@router.post("/create-case", response_model=CaseOut, status_code=201)
async def create_case_from_intake(
    data: IntakeCreateCaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """维权前台：根据分析结果一键建案。"""
    case_type = data.case_type or "administrative_labor"
    if case_type not in ALLOWED_CASE_TYPES:
        raise HTTPException(400, f"无效案件类型: {case_type}")

    try:
        case = Case(
            title=data.title.strip(),
            case_type=case_type,
            description=data.description,
            plaintiff=data.plaintiff,
            defendant=data.defendant,
            owner_id=current_user.id,
            team_id=current_user.team_id,
            status="active",
        )
        db.add(case)
        await db.flush()
        await bind_intake_to_new_case(
            db,
            case,
            current_user.id,
            cause_type_override=data.cause_type,
        )
        await db.flush()
        await db.refresh(case)
        return CaseOut.model_validate(_case_to_out(case, 0))
    except Exception as exc:
        logger.error("Intake create case failed: %s", exc)
        await db.rollback()
        raise HTTPException(500, "创建案件失败")
