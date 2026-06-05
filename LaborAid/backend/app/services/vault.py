"""材料库：配额校验与写入"""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user_material import UserMaterial

ALLOWED_STAGES = {"preparation", "complaint", "arbitration", "mediation", "closed"}
ALLOWED_SOURCES = {"manual", "evidence", "contract", "document", "knowledge"}


async def get_user_vault_usage(db: AsyncSession, user_id: int) -> tuple[int, int]:
    row = await db.execute(
        select(func.count(UserMaterial.id), func.coalesce(func.sum(UserMaterial.size_bytes), 0)).where(
            UserMaterial.user_id == user_id,
            UserMaterial.deleted_at.is_(None),
        )
    )
    count, total = row.one()
    return int(count or 0), int(total or 0)


async def assert_vault_quota(db: AsyncSession, user_id: int, add_bytes: int) -> None:
    settings = get_settings()
    quota_bytes = settings.VAULT_QUOTA_MB * 1024 * 1024
    max_files = settings.VAULT_MAX_FILES

    count, total = await get_user_vault_usage(db, user_id)
    if count >= max_files:
        raise ValueError(f"材料库文件数已达上限（{max_files}）")
    if total + add_bytes > quota_bytes:
        raise ValueError(f"材料库容量不足（上限 {settings.VAULT_QUOTA_MB} MB）")


def vault_dest_path(user_id: int, original_filename: str) -> tuple[Path, str]:
    settings = get_settings()
    ext = Path(original_filename or ".bin").suffix
    safe_name = f"{uuid.uuid4().hex}{ext}"
    rel = f"vault/{user_id}/{safe_name}"
    dest = settings.upload_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest, rel


def _soft_delete_rows(rows: list[UserMaterial]) -> int:
    now = datetime.now(timezone.utc)
    n = 0
    for row in rows:
        if row.deleted_at is None:
            row.deleted_at = now
            n += 1
    return n


async def mark_vault_source_deleted(
    db: AsyncSession,
    *,
    user_id: int,
    source: str,
    source_id: int,
) -> None:
    """同一证据/来源重新上传时，软删除旧材料库副本。"""
    result = await db.execute(
        select(UserMaterial).where(
            UserMaterial.user_id == user_id,
            UserMaterial.source == source,
            UserMaterial.source_id == source_id,
            UserMaterial.deleted_at.is_(None),
        )
    )
    _soft_delete_rows(list(result.scalars().all()))


async def soft_delete_materials_for_case(
    db: AsyncSession,
    *,
    user_id: int,
    case_id: int,
    evidence_ids: list[int] | None = None,
) -> int:
    """删除案件时：软删除关联材料库条目（按 case_id 及证据 source_id）。"""
    deleted = 0
    by_case = await db.execute(
        select(UserMaterial).where(
            UserMaterial.user_id == user_id,
            UserMaterial.case_id == case_id,
            UserMaterial.deleted_at.is_(None),
        )
    )
    deleted += _soft_delete_rows(list(by_case.scalars().all()))

    if evidence_ids:
        by_evidence = await db.execute(
            select(UserMaterial).where(
                UserMaterial.user_id == user_id,
                UserMaterial.source == "evidence",
                UserMaterial.source_id.in_(evidence_ids),
                UserMaterial.deleted_at.is_(None),
            )
        )
        deleted += _soft_delete_rows(list(by_evidence.scalars().all()))

    return deleted


async def archive_file_to_vault(
    db: AsyncSession,
    *,
    user_id: int,
    content: bytes,
    original_filename: str,
    source: str,
    source_id: int | None = None,
    case_id: int | None = None,
    stage: str = "preparation",
    mime_type: str | None = None,
    replace_existing: bool = True,
    commit: bool = True,
) -> UserMaterial | None:
    """从整理证据等模块归集副本到材料库；配额不足时跳过。"""
    if source not in ALLOWED_SOURCES:
        source = "manual"
    if replace_existing and source_id is not None:
        await mark_vault_source_deleted(db, user_id=user_id, source=source, source_id=source_id)
    try:
        await assert_vault_quota(db, user_id, len(content))
    except ValueError:
        return None

    dest, rel = vault_dest_path(user_id, original_filename)
    await asyncio.to_thread(dest.write_bytes, content)

    title = Path(original_filename).stem[:500] or original_filename
    row = UserMaterial(
        user_id=user_id,
        case_id=case_id,
        source=source,
        source_id=source_id,
        title=title,
        original_filename=original_filename,
        stored_path=rel,
        mime_type=mime_type,
        size_bytes=len(content),
        stage=stage,
    )
    db.add(row)
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(row)
    return row
