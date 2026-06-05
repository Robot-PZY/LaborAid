"""根据案情与证据推荐应生成的文书类型。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.document import Document
from app.models.evidence import Evidence
from app.services.docgen.types import normalize_doc_type
from app.services.intake.analyzer import (
    _BUNDLE_TYPE_LABELS,
    _DOC_TYPE_MAP,
    _cause_label,
    _match_cause,
    _recommend_docgen_prefill,
)
from app.services.intake.case_binding import resolve_intake_context
from app.services.orchestrator.doc_facts import build_docgen_case_facts

# 与前端 doc-types 标签一致
DOC_TYPE_LABELS: dict[str, str] = {
    "application": "劳动仲裁申请书",
    "labor_supervision": "劳动监察投诉书",
    "wage_demand_letter": "工资催告函",
    "forced_termination_notice": "被迫解除劳动合同通知书",
    "arbitration_authorization": "劳动仲裁代理委托书",
    "evidence_list": "证据清单",
    "labor_contract": "劳动合同",
    "mediation": "劳动争议调解协议书",
    "settlement_agreement": "劳动争议和解协议",
    "complaint": "民事起诉状",
    "answer": "答辩状",
    "appeal": "上诉状",
    "agency_opinion": "代理词",
    "legal_opinion": "法律意见书",
    "lawyer_letter": "律师函",
    "contract": "通用民事合同",
    "preservation_application": "财产保全申请书",
    "other": "其他文书",
}

DOC_TYPE_REASONS: dict[str, str] = {
    "application": "核心维权文书，向劳动人事争议仲裁委员会申请仲裁",
    "evidence_list": "整理已上传证据，列明证明目的，便于提交仲裁或诉讼",
    "labor_supervision": "向人社监察部门书面投诉，督促用人单位支付欠薪",
    "wage_demand_letter": "书面催告用人单位限期支付工资，固定催讨记录",
    "forced_termination_notice": "用人单位存在法定过错时，劳动者书面解除合同",
    "arbitration_authorization": "委托代理人参加仲裁时使用",
    "complaint": "劳动仲裁后不服裁决或符合直接起诉条件时向法院起诉",
    "mediation": "经调解组织主持达成协议时使用",
    "settlement_agreement": "双方自行和解一次性了结争议",
}


def _extra_doc_types(cause_type: str, text: str, channel_id: str | None, scenario_id: str | None) -> list[str]:
    """按通道/关键词补充推荐。"""
    extras: list[str] = []
    lowered = text.lower()
    if cause_type == "wage_arrears":
        if any(kw in text for kw in ["监察", "已投诉", "举报"]):
            extras.append("labor_supervision")
        elif any(kw in text for kw in ["包工头", "工地", "劳务"]):
            extras.append("wage_demand_letter")
        if channel_id == "migrant-worker" and scenario_id in ("wage_boss", "subcontract", "project_stop"):
            if "labor_supervision" not in extras:
                extras.append("wage_demand_letter")
    if cause_type == "illegal_termination" and any(kw in lowered for kw in ["被迫", "违法解除"]):
        if "forced_termination_notice" not in extras:
            extras.insert(0, "forced_termination_notice")
    return extras


def build_doc_recommendations(
    *,
    case_facts: str,
    cause_type: str | None = None,
    channel_id: str | None = None,
    scenario_id: str | None = None,
    existing_doc_types: set[str] | None = None,
    evidence_count: int = 0,
) -> dict:
    text = (case_facts or "").strip()
    cause = cause_type or _match_cause(text)
    summary = text.split("\n")[0][:120] if text else _cause_label(cause)

    prefill = _recommend_docgen_prefill(cause, text, summary)
    bundle = list(prefill.get("bundleDocTypes") or [])
    if not bundle:
        base = str(prefill.get("docType") or _DOC_TYPE_MAP.get(cause, "application"))
        bundle = [base]

    for extra in _extra_doc_types(cause, text, channel_id, scenario_id):
        if extra not in bundle:
            bundle.append(extra)

    # 有证据时优先推荐证据清单（若尚未包含）
    if evidence_count > 0 and "evidence_list" not in bundle:
        bundle.append("evidence_list")

    bundle = list(dict.fromkeys(bundle))
    existing = existing_doc_types or set()

    recommendations = []
    for idx, doc_type in enumerate(bundle):
        canonical = normalize_doc_type(doc_type) or doc_type
        recommendations.append({
            "doc_type": canonical,
            "label": DOC_TYPE_LABELS.get(canonical, canonical),
            "reason": DOC_TYPE_REASONS.get(
                canonical,
                f"适用于{_cause_label(cause)}类纠纷",
            ),
            "priority": idx + 1,
            "generated": canonical in existing,
        })

    analysis_bits = [f"案由倾向：{_cause_label(cause)}"]
    if evidence_count > 0:
        analysis_bits.append(f"已关联 {evidence_count} 份证据材料")
    else:
        analysis_bits.append("尚未上传证据，建议同步整理证据清单")
    if channel_id:
        analysis_bits.append("来自专项维权通道案情")

    return {
        "cause_type": cause,
        "cause_label": _cause_label(cause),
        "summary": "；".join(analysis_bits) + "。",
        "recommendations": recommendations,
    }


async def recommend_docs_for_case(
    db: AsyncSession,
    case: Case,
    *,
    intake_session: dict | None = None,
) -> dict:
    facts = await build_docgen_case_facts(db, case)
    ctx = resolve_intake_context(case, intake_session)

    evid_count_q = await db.execute(
        select(Evidence.id).where(Evidence.case_id == case.id)
    )
    evidence_count = len(evid_count_q.scalars().all())

    docs = (
        await db.execute(select(Document.type).where(Document.case_id == case.id))
    ).scalars().all()
    existing = {normalize_doc_type(t) or t for t in docs if t}

    result = build_doc_recommendations(
        case_facts=facts,
        cause_type=ctx.get("cause_type"),
        channel_id=ctx.get("channel_id"),
        scenario_id=ctx.get("scenario_id"),
        existing_doc_types=existing,
        evidence_count=evidence_count,
    )
    result["case_facts_preview"] = facts[:500] + ("..." if len(facts) > 500 else "")
    return result
