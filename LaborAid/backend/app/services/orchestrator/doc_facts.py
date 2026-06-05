"""为文书生成聚合案情与证据摘要。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.evidence import Evidence


async def build_docgen_case_facts(
    db: AsyncSession,
    case: Case,
    *,
    user_provided: str | None = None,
    max_len: int = 12000,
) -> str:
    """合并用户输入、案件描述与证据分析/ OCR 摘要。"""
    parts: list[str] = []

    if user_provided and user_provided.strip():
        parts.append(user_provided.strip())
    elif case.description and case.description.strip():
        parts.append(case.description.strip())

    if case.plaintiff or case.defendant:
        parts.append(
            f"【当事人】申请人/原告：{case.plaintiff or '待填写'}；"
            f"被申请人/被告：{case.defendant or '待填写'}"
        )

    rows = (
        await db.execute(
            select(Evidence)
            .where(Evidence.case_id == case.id)
            .order_by(Evidence.sort_order.asc(), Evidence.id.asc())
            .limit(15)
        )
    ).scalars().all()

    if rows:
        lines: list[str] = []
        for ev in rows:
            snippet = ""
            if ev.analysis and ev.analysis.strip():
                snippet = ev.analysis.strip().replace("\n", " ")[:180]
            elif ev.ocr_text and ev.ocr_text.strip():
                snippet = ev.ocr_text.strip().replace("\n", " ")[:120]
            if snippet:
                lines.append(f"- {ev.title}：{snippet}")
            else:
                lines.append(f"- {ev.title}")
        parts.append("【证据材料】\n" + "\n".join(lines))

    text = "\n\n".join(p for p in parts if p).strip()
    if len(text) < 10:
        text = (user_provided or case.description or case.title or "劳动争议维权案件").strip()
    return text[:max_len]
