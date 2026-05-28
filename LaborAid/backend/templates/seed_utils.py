"""Shared helpers for idempotent template seeding."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

COMMON_FORMAT = {
    "font": "仿宋",
    "size": 14,
    "line_spacing": 28,
    "margins": [37, 28, 35, 26],
    "title_font": "黑体",
    "title_size": 22,
    "subtitle_font": "楷体",
    "subtitle_size": 16,
    "paper": "A4",
}


def get_sync_engine():
    import os

    sync_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not sync_url:
        try:
            from app.config import get_settings

            sync_url = get_settings().DATABASE_URL_SYNC
        except Exception:
            sync_url = "sqlite:///./laboraid.db"
    sync_url = sync_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    return create_engine(sync_url, echo=False)


def ensure_tables(engine) -> None:
    try:
        from app.core.database import Base
        import app.models  # noqa: F401

        Base.metadata.create_all(engine)
    except Exception:
        pass


def seed_template_records(
    templates: list[dict],
    *,
    match: str = "name",
) -> dict[str, int]:
    """
    Insert or update public platform templates.

    match=name: skip if same name exists (legacy labor seed).
    match=type: upsert single public template per type (platform pack).
    """
    engine = get_sync_engine()
    ensure_tables(engine)

    inserted = updated = skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    insert_sql = text("""
        INSERT INTO templates (name, type, description, structure, ai_prompt, format_rules, variables, is_public, created_at, updated_at)
        VALUES (:name, :type, :description, :structure, :ai_prompt, :format_rules, :variables, TRUE, :created_at, :updated_at)
    """)
    update_sql = text("""
        UPDATE templates
        SET name = :name, description = :description, structure = :structure,
            ai_prompt = :ai_prompt, format_rules = :format_rules, variables = :variables,
            updated_at = :updated_at
        WHERE id = :id
    """)

    with Session(engine) as session:
        for tpl in templates:
            payload = {
                "name": tpl["name"],
                "type": tpl["type"],
                "description": tpl["description"],
                "structure": json.dumps(tpl["structure"], ensure_ascii=False),
                "ai_prompt": tpl["ai_prompt"],
                "format_rules": json.dumps(tpl.get("format_rules") or COMMON_FORMAT, ensure_ascii=False),
                "variables": json.dumps(tpl.get("variables") or [], ensure_ascii=False),
                "created_at": now,
                "updated_at": now,
            }

            if match == "type":
                row = session.execute(
                    text("SELECT id FROM templates WHERE type = :type AND is_public = 1 ORDER BY id ASC LIMIT 1"),
                    {"type": tpl["type"]},
                ).scalar_one_or_none()
                if row is not None:
                    session.execute(update_sql, {**payload, "id": row})
                    updated += 1
                    continue
            else:
                row = session.execute(
                    text("SELECT id FROM templates WHERE name = :name"),
                    {"name": tpl["name"]},
                ).scalar_one_or_none()
                if row is not None:
                    skipped += 1
                    continue

            session.execute(insert_sql, payload)
            inserted += 1

        session.commit()

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "total": len(templates)}
