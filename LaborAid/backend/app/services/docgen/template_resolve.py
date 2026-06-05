"""按文书类型解析模板（含平台模板包自动同步）。"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Template
from app.services.docgen.types import normalize_doc_type

logger = logging.getLogger(__name__)


async def resolve_template_for_doc_type(
    db: AsyncSession,
    doc_type: str,
    *,
    template_id: int | None = None,
    owner_id: int | None = None,
) -> Template | None:
    if template_id is not None:
        template = await db.get(Template, template_id)
        if template and not template.is_public and owner_id is not None and template.owner_id != owner_id:
            return None
        return template

    canonical = normalize_doc_type(doc_type) or doc_type
    result = await db.execute(
        select(Template)
        .where(Template.type == canonical)
        .order_by(Template.is_public.desc(), Template.id.asc())
        .limit(1)
    )
    template = result.scalar_one_or_none()
    if template:
        return template

    try:
        from app.services.bootstrap_templates import ensure_platform_templates

        ensure_platform_templates()
        retry = await db.execute(
            select(Template)
            .where(Template.type == canonical)
            .order_by(Template.is_public.desc(), Template.id.asc())
            .limit(1)
        )
        return retry.scalar_one_or_none()
    except Exception as exc:
        logger.warning("Template bootstrap retry failed: %s", exc)
        return None
