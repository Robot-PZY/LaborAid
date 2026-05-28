"""删除文书时清理磁盘上的导出缓存。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def cleanup_document_files(
    doc_id: int,
    *,
    exported_path: str | None = None,
    uploads_root: Path,
) -> int:
    """
    删除与文书 ID 关联的导出文件（docx/html/pdf/md）。
    返回已删除文件数量。
    """
    removed = 0
    exports_dir = uploads_root / "exports"
    if not exports_dir.is_dir():
        exports_dir = uploads_root

    def _unlink(path: Path) -> bool:
        nonlocal removed
        try:
            if path.is_file():
                path.unlink()
                removed += 1
                return True
        except OSError as e:
            logger.warning("Failed to remove export file %s: %s", path, e)
        return False

    def _scan() -> None:
        if exported_path:
            p = Path(exported_path)
            if p.is_file():
                try:
                    p.resolve().relative_to(exports_dir.resolve())
                    _unlink(p)
                except ValueError:
                    logger.warning("Skip exported_path outside exports dir: %s", p)

        if exports_dir.is_dir():
            for pattern in (f"{doc_id}_*", f"{doc_id}.*"):
                for path in exports_dir.glob(pattern):
                    if path.is_file():
                        _unlink(path)

    await asyncio.to_thread(_scan)
    return removed
