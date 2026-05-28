"""平台知识库预置条目 — 从 JSON 幂等导入。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_platform_seed.json"


def _get_sync_engine():
    import os

    sync_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not sync_url:
        from app.config import get_settings

        sync_url = get_settings().DATABASE_URL_SYNC
    sync_url = sync_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    return create_engine(sync_url, echo=False)


def load_seed_items() -> list[dict]:
    if not _DATA_PATH.is_file():
        logger.warning("Knowledge seed file not found: %s", _DATA_PATH)
        return []
    raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return list(raw.get("items") or [])


def seed_platform_knowledge() -> dict[str, int]:
    """按 seed_key 幂等插入 is_platform=True 的知识条目。"""
    items = load_seed_items()
    if not items:
        return {"inserted": 0, "skipped": 0, "total": 0}

    try:
        from app.core.database import Base
        import app.models  # noqa: F401

        engine = _get_sync_engine()
        Base.metadata.create_all(engine)
    except Exception as exc:
        logger.warning("Knowledge seed table init: %s", exc)
        engine = _get_sync_engine()

    inserted = 0
    skipped = 0

    with Session(engine) as session:
        for item in items:
            title = item.get("title")
            if not title:
                continue
            existing = session.execute(
                text(
                    "SELECT id FROM knowledge_items "
                    "WHERE is_platform = 1 AND title = :title LIMIT 1"
                ),
                {"title": title},
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

            tags = list(item.get("tags") or [])
            now = datetime.now(timezone.utc).isoformat()

            session.execute(
                text(
                    """
                    INSERT INTO knowledge_items
                    (title, content, source, tags, is_platform, owner_id, team_id, created_at)
                    VALUES (:title, :content, :source, :tags, 1, NULL, NULL, :created_at)
                    """
                ),
                {
                    "title": title,
                    "content": item["content"],
                    "source": item.get("source") or "劳权智助平台",
                    "tags": json.dumps(tags, ensure_ascii=False),
                    "created_at": now,
                },
            )
            inserted += 1
        session.commit()

    return {"inserted": inserted, "skipped": skipped, "total": len(items)}


async def seed_platform_knowledge_async(db) -> dict[str, int]:
    """异步会话版本，供 API 调用。"""
    from app.models.knowledge import KnowledgeItem

    items = load_seed_items()
    inserted = 0
    skipped = 0

    for item in items:
        title = item.get("title")
        if not title:
            continue
        tags = list(item.get("tags") or [])

        result = await db.execute(
            select(KnowledgeItem.id).where(
                KnowledgeItem.is_platform.is_(True),
                KnowledgeItem.title == title,
            )
        )
        if result.scalar_one_or_none() is not None:
            skipped += 1
            continue

        row = KnowledgeItem(
            title=title,
            content=item["content"],
            source=item.get("source") or "劳权智助平台",
            tags=tags,
            is_platform=True,
            owner_id=None,
            team_id=None,
        )
        db.add(row)
        inserted += 1

    if inserted:
        await db.commit()
        from app.core.cache import invalidate_on_create

        invalidate_on_create("knowledge", "platform")

    return {"inserted": inserted, "skipped": skipped, "total": len(items)}
