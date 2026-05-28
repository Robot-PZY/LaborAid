"""Resolve per-user LLM configuration for agent API calls.

All end users share **system-level** LLM profiles managed in the admin console.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.services.llm_client import create_llm_client, create_llm_client_from_settings
from app.services.system_user import get_system_user


@dataclass
class ResolvedLLM:
    client: Any
    model: str
    max_tokens: int
    config_name: str
    source: Literal["database", "env"]
    config_id: int | None = None
    base_url: str = ""
    api_key: str = ""


async def _resolve_system_llm_row(
    db: AsyncSession,
    *,
    config_id: int | None = None,
    vision_only: bool = False,
):
    from app.models.llm_settings import LLMSettings
    from app.api.routers.llm_settings import ensure_system_llm_defaults
    from app.services.llm_profiles import is_ocr_profile, is_vision_profile

    system = await get_system_user(db)
    await ensure_system_llm_defaults(db)

    if config_id is not None:
        result = await db.execute(
            select(LLMSettings).where(
                LLMSettings.id == config_id,
                LLMSettings.owner_id == system.id,
            )
        )
        return result.scalar_one_or_none()

    result = await db.execute(
        select(LLMSettings).where(LLMSettings.owner_id == system.id)
    )
    rows = result.scalars().all()
    if vision_only:
        vision_rows = [
            row for row in rows
            if row.api_key and is_vision_profile(row.name, row.model_name)
        ]
        ocr_rows = [
            row for row in vision_rows
            if is_ocr_profile(row.name, row.model_name)
        ]
        for pool in (ocr_rows, vision_rows):
            if not pool:
                continue
            for row in pool:
                if row.is_default:
                    return row
            return pool[0]
        return None

    for row in rows:
        if row.is_default and row.api_key:
            return row
    return None


async def resolve_user_llm(
    db: AsyncSession,
    user: User,  # noqa: ARG001 — kept for API compatibility
    config_id: int | None = None,
) -> ResolvedLLM:
    """Resolve global text LLM (admin-managed system profile, else .env)."""
    row = await _resolve_system_llm_row(db, config_id=config_id, vision_only=False)

    if row and row.api_key:
        return ResolvedLLM(
            client=create_llm_client(row.base_url, row.api_key),
            model=row.model_name,
            max_tokens=row.max_tokens,
            config_name=row.name,
            source="database",
            config_id=row.id,
            base_url=row.base_url,
            api_key=row.api_key,
        )

    settings = get_settings()
    return ResolvedLLM(
        client=create_llm_client_from_settings(settings),
        model=settings.LLM_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        config_name="环境变量",
        source="env",
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )


async def resolve_vision_llm(
    db: AsyncSession,
    user: User,  # noqa: ARG001
) -> ResolvedLLM:
    """Resolve LLM for image OCR — system vision profile, then VISION_LLM_* env."""
    row = await _resolve_system_llm_row(db, vision_only=True)

    if row and row.api_key:
        return ResolvedLLM(
            client=create_llm_client(row.base_url, row.api_key),
            model=row.model_name,
            max_tokens=row.max_tokens,
            config_name=row.name,
            source="database",
            config_id=row.id,
            base_url=row.base_url,
            api_key=row.api_key,
        )

    settings = get_settings()
    vision_cfg = settings.get_vision_llm_config()
    if vision_cfg["api_key"]:
        return ResolvedLLM(
            client=create_llm_client(vision_cfg["base_url"], vision_cfg["api_key"]),
            model=vision_cfg["model"],
            max_tokens=vision_cfg["max_tokens"],
            config_name="通义视觉（环境变量）",
            source="env",
            base_url=vision_cfg["base_url"],
            api_key=vision_cfg["api_key"],
        )

    return ResolvedLLM(
        client=None,
        model="",
        max_tokens=4096,
        config_name="未配置视觉/OCR 模型",
        source="env",
        config_id=None,
        base_url="",
        api_key="",
    )
