"""个人材料库 API"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, validate_upload
from app.models.user import User
from app.models.user_material import UserMaterial
from app.schemas.vault import (
    UserMaterialOut,
    UserMaterialUpdate,
    VaultBulkDeleteIn,
    VaultBulkDeleteOut,
    VaultStatsOut,
)
from app.services.vault import (
    ALLOWED_STAGES,
    assert_vault_quota,
    get_user_vault_usage,
    vault_dest_path,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _active_filter():
    return UserMaterial.deleted_at.is_(None)


@router.get("/stats", response_model=VaultStatsOut)
async def vault_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    count, total = await get_user_vault_usage(db, current_user.id)

    stage_rows = await db.execute(
        select(UserMaterial.stage, func.count())
        .where(UserMaterial.user_id == current_user.id, _active_filter())
        .group_by(UserMaterial.stage)
    )
    by_stage = {str(s): int(c) for s, c in stage_rows.all()}

    return VaultStatsOut(
        total_files=count,
        total_bytes=total,
        quota_bytes=settings.VAULT_QUOTA_MB * 1024 * 1024,
        by_stage=by_stage,
    )


@router.get("", response_model=list[UserMaterialOut])
async def list_materials(
    stage: str | None = None,
    source: str | None = None,
    case_id: int | None = None,
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(UserMaterial)
        .where(UserMaterial.user_id == current_user.id, _active_filter())
        .order_by(UserMaterial.created_at.desc())
    )
    if stage:
        query = query.where(UserMaterial.stage == stage)
    if source:
        query = query.where(UserMaterial.source == source)
    if case_id is not None:
        query = query.where(UserMaterial.case_id == case_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(
            UserMaterial.title.ilike(like) | UserMaterial.original_filename.ilike(like)
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/upload", response_model=UserMaterialOut, status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    stage: str = Query("preparation"),
    case_id: int | None = Query(None),
    note: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if stage not in ALLOWED_STAGES:
        raise HTTPException(400, "无效的维权阶段")

    try:
        content = await validate_upload(file)
        await assert_vault_quota(db, current_user.id, len(content))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    fname = file.filename or "未命名文件"
    dest, rel = vault_dest_path(current_user.id, fname)
    await asyncio.to_thread(dest.write_bytes, content)

    row = UserMaterial(
        user_id=current_user.id,
        case_id=case_id,
        source="manual",
        title=Path(fname).stem[:500] or fname,
        original_filename=fname,
        stored_path=rel,
        mime_type=file.content_type,
        size_bytes=len(content),
        stage=stage,
        note=note,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except Exception as e:
        await db.rollback()
        dest.unlink(missing_ok=True)
        logger.error("Vault upload save failed: %s", e)
        raise HTTPException(500, "保存材料失败") from e

    return row


@router.get("/{material_id}", response_model=UserMaterialOut)
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await _get_owned(db, current_user.id, material_id)
    return row


@router.get("/{material_id}/download")
async def download_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await _get_owned(db, current_user.id, material_id)
    settings = get_settings()
    fp = settings.upload_path / row.stored_path
    if not fp.is_file():
        raise HTTPException(404, "文件不存在或已损坏")
    return FileResponse(
        str(fp),
        filename=row.original_filename,
        media_type=row.mime_type or "application/octet-stream",
    )


@router.patch("/{material_id}", response_model=UserMaterialOut)
async def update_material(
    material_id: int,
    data: UserMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await _get_owned(db, current_user.id, material_id)
    if data.title is not None:
        row.title = data.title.strip()[:500]
    if data.stage is not None:
        if data.stage not in ALLOWED_STAGES:
            raise HTTPException(400, "无效的维权阶段")
        row.stage = data.stage
    if data.case_id is not None:
        row.case_id = data.case_id
    if data.tags is not None:
        row.tags = data.tags
    if data.note is not None:
        row.note = data.note
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/bulk-delete", response_model=VaultBulkDeleteOut)
async def bulk_delete_materials(
    data: VaultBulkDeleteIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量软删除材料（最多 100 条）。"""
    from datetime import datetime, timezone

    unique_ids = list(dict.fromkeys(data.ids))
    result = await db.execute(
        select(UserMaterial).where(
            UserMaterial.id.in_(unique_ids),
            UserMaterial.user_id == current_user.id,
            _active_filter(),
        )
    )
    rows = list(result.scalars().all())
    now = datetime.now(timezone.utc)
    for row in rows:
        row.deleted_at = now
    await db.commit()
    return VaultBulkDeleteOut(deleted=len(rows))


@router.delete("/{material_id}", status_code=204)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone

    row = await _get_owned(db, current_user.id, material_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def _get_owned(db: AsyncSession, user_id: int, material_id: int) -> UserMaterial:
    result = await db.execute(
        select(UserMaterial).where(
            UserMaterial.id == material_id,
            UserMaterial.user_id == user_id,
            _active_filter(),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "材料不存在")
    return row
