"""Ensure platform knowledge seed bundle exists."""

import logging

logger = logging.getLogger(__name__)


def ensure_platform_knowledge() -> None:
    try:
        from app.services.seed_platform_knowledge import seed_platform_knowledge

        result = seed_platform_knowledge()
        logger.info(
            "Platform knowledge seed: inserted=%s skipped=%s total=%s",
            result.get("inserted"),
            result.get("skipped"),
            result.get("total"),
        )
    except Exception as exc:
        logger.warning("Failed to seed platform knowledge: %s", exc)
