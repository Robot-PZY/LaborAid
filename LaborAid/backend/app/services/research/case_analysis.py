"""基于案件档案、文书、证据生成维权案情总结报告。"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.research import ResearchReport
from app.services.intake.case_binding import get_case_intake
from app.services.llm_resolver import ResolvedLLM

logger = logging.getLogger(__name__)

CONCLUSION_LEVELS = (
    "信息不足需补充",
    "继续完善材料",
    "可以准备劳动仲裁或监察投诉",
    "可以准备法院起诉",
)

CASE_REPORT_SYSTEM = """你是劳动维权与民事诉讼辅助专家。根据用户案件档案及已上传材料，撰写「案情分析总结报告」。
要求：
1. 使用 Markdown，语言通俗、结构清晰，面向劳动者本人阅读。
2. 不要编造材料中不存在的姓名、金额、日期；缺失处写「（材料未提供）」。
3. 报告必须以「## 维权阶段结论」开头（紧接在标题后），其中必须包含：
   - **结论等级**：（仅从以下选一）信息不足需补充 / 继续完善材料 / 可以准备劳动仲裁或监察投诉 / 可以准备法院起诉
   - **一句话总结**：（30字以内）
4. 禁止问候语、禁止自称 AI 或劳权智助。
5. 若材料极少，结论等级应为「信息不足需补充」或「继续完善材料」，并列出待办。"""


async def gather_case_materials(
    db: AsyncSession,
    case: Case,
    *,
    owner_id: int,
) -> dict[str, Any]:
    docs = (
        await db.execute(
            select(Document)
            .where(Document.case_id == case.id, Document.owner_id == owner_id)
            .order_by(Document.updated_at.desc())
            .limit(20)
        )
    ).scalars().all()

    evidence_rows = (
        await db.execute(
            select(Evidence).where(Evidence.case_id == case.id).order_by(Evidence.created_at.desc()).limit(30)
        )
    ).scalars().all()

    prior_reports = (
        await db.execute(
            select(ResearchReport)
            .where(ResearchReport.case_id == case.id, ResearchReport.owner_id == owner_id)
            .order_by(ResearchReport.created_at.desc())
            .limit(3)
        )
    ).scalars().all()

    intake = get_case_intake(case)
    intake_summary = (intake.get("summary") or "").strip()

    return {
        "case": case,
        "documents": docs,
        "evidence": evidence_rows,
        "prior_reports": prior_reports,
        "intake": intake,
        "stats": {
            "documents": len(docs),
            "evidence": len(evidence_rows),
            "has_description": bool((case.description or "").strip()),
            "has_intake_summary": bool(intake_summary),
        },
    }


def _format_materials_block(materials: dict[str, Any]) -> str:
    case: Case = materials["case"]
    intake = materials.get("intake") or {}
    lines = [
        f"案件标题：{case.title}",
        f"案件类型：{case.case_type}",
        f"状态：{case.status}",
        f"申请人/原告：{case.plaintiff or '（未填写）'}",
        f"被申请人/被告：{case.defendant or '（未填写）'}",
        f"案情描述：\n{case.description or '（未填写）'}",
    ]
    if intake.get("cause_label") or intake.get("cause_type"):
        lines.append(
            f"维权 intake：{intake.get('cause_label') or intake.get('cause_type')} "
            f"（通道 {intake.get('channel_id') or '—'} / 情形 {intake.get('scenario_id') or '—'}）"
        )
    if intake.get("summary"):
        lines.append(f"intake 案情摘要：\n{intake['summary']}")
    if intake.get("evidence_checklist"):
        lines.append("建议证据清单：" + "；".join(str(x) for x in intake["evidence_checklist"][:12]))
    lines.extend(["", f"关联文书 {materials['stats']['documents']} 份："])
    for doc in materials["documents"]:
        excerpt = (doc.content or "")[:2500]
        lines.append(f"- 【{doc.title}】类型={doc.type}，状态={doc.status}\n{excerpt}")
    if not materials["documents"]:
        lines.append("- （暂无）")

    lines.append("")
    lines.append(f"关联证据 {materials['stats']['evidence']} 项：")
    for ev in materials["evidence"]:
        ocr = (ev.ocr_text or "")[:1500]
        analysis = (ev.analysis or "").strip()[:200]
        extra = f"\nAI摘要：{analysis}" if analysis else ""
        lines.append(
            f"- 【{ev.title or '未命名证据'}】类型={ev.type or '—'}；"
            f"说明={getattr(ev, 'description', None) or '—'}\n{ocr or '（无 OCR 文字）'}{extra}"
        )
    if not materials["evidence"]:
        lines.append("- （暂无）")

    if materials["prior_reports"]:
        lines.append("")
        lines.append("近期案情分析报告摘要：")
        for r in materials["prior_reports"]:
            lines.append(f"- {r.query}: {(r.report or '')[:400]}…")

    return "\n".join(lines)


def parse_conclusion_level(report: str) -> str | None:
    m = re.search(
        r"结论等级[」\*]*[：:]\s*[「\*]*(.+?)[」\*]*\s*(?:\n|$)",
        report,
    )
    if not m:
        return None
    text = m.group(1).strip().strip("[]【】")
    for level in CONCLUSION_LEVELS:
        if level in text:
            return level
    return text[:80] if text else None


async def generate_case_analysis_report(
    db: AsyncSession,
    case: Case,
    *,
    owner_id: int,
    llm: ResolvedLLM,
    extra_notes: str | None = None,
) -> dict[str, Any]:
    materials = await gather_case_materials(db, case, owner_id=owner_id)
    stats = materials["stats"]

    if (
        not stats["has_description"]
        and stats["documents"] == 0
        and stats["evidence"] == 0
        and not stats.get("has_intake_summary")
    ):
        raise ValueError("案件尚无案情描述、维权摘要、文书或证据，请先补充至少一项后再分析")

    user_prompt = f"""请根据以下案件全部已知信息，生成一份完整的案情分析总结报告。

{ _format_materials_block(materials) }

## 用户补充说明
{extra_notes.strip() if extra_notes and extra_notes.strip() else "（无）"}

请按系统要求输出 Markdown 报告。"""

    try:
        response = await llm.client.messages.create(
            model=llm.model,
            max_tokens=min(llm.max_tokens, 8192),
            system=CASE_REPORT_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        report = response.content[0].text if response.content else ""
    except Exception as e:
        logger.exception("Case analysis LLM failed: %s", e)
        raise RuntimeError("案情分析生成失败，请稍后重试") from e

    if not report.strip():
        raise RuntimeError("案情分析生成结果为空")

    conclusion = parse_conclusion_level(report)
    title_query = f"[案情分析] {case.title}"

    return {
        "report": report,
        "query": title_query,
        "sources_used": [
            "case_profile",
            f"documents:{stats['documents']}",
            f"evidence:{stats['evidence']}",
        ],
        "conclusion_level": conclusion,
        "stats": stats,
    }
