"""Lightweight SQLite schema upgrades (create_all does not alter existing tables)."""

import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def run_schema_migrations(sync_conn) -> None:
    insp = inspect(sync_conn)
    if "knowledge_items" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("knowledge_items")}
    if "is_platform" not in cols:
        sync_conn.execute(
            text(
                "ALTER TABLE knowledge_items "
                "ADD COLUMN is_platform BOOLEAN NOT NULL DEFAULT 0"
            )
        )
        logger.info("Added knowledge_items.is_platform column")
