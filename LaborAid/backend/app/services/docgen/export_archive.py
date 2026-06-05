"""文书导出为 Word 并归档到材料库。"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document

logger = logging.getLogger(__name__)

_SAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_export_filename(title: str, ext: str = "docx") -> str:
    base = _SAFE_FILENAME_RE.sub("_", (title or "法律文书").strip())[:80] or "法律文书"
    return f"{base}.{ext}"


async def export_docx_and_archive(
    db: AsyncSession,
    doc: Document,
    *,
    user_id: int,
) -> bool:
    """生成 Word 文件、更新 exported_path，并在材料库保留副本。"""
    from app.services.docgen.word_export import export_to_docx
    from app.services.vault import archive_file_to_vault

    settings = get_settings()
    output_dir = settings.upload_path / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        filepath = await export_to_docx(doc, output_dir)
        path = Path(filepath)
        if not path.is_file():
            return False

        content = await asyncio.to_thread(path.read_bytes)
        doc.exported_path = f"exports/{path.name}"
        doc.status = doc.status or "generated"
        if doc.status == "generated":
            doc.status = "exported"

        filename = _safe_export_filename(doc.title)
        row = await archive_file_to_vault(
            db,
            user_id=user_id,
            content=content,
            original_filename=filename,
            source="document",
            source_id=doc.id,
            case_id=doc.case_id,
            stage="complaint",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            commit=False,
        )
        await db.flush()
        return row is not None
    except Exception as exc:
        logger.warning("export_docx_and_archive failed for doc %s: %s", doc.id, exc)
        return False
