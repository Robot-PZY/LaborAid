"""Ensure platform document templates exist (worker-focused defaults)."""

import logging

logger = logging.getLogger(__name__)


def ensure_platform_templates() -> None:
    """Idempotent seed of public document templates (upsert by type)."""
    try:
        from templates.seed_platform_pack import seed_platform_pack

        result = seed_platform_pack()
        logger.info("Platform document template pack: %s", result)
    except Exception as exc:
        logger.warning("Failed to seed platform template pack: %s", exc)
