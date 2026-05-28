"""结构化 payload 后处理：案情补全、研究摘要、仲裁委推断等。"""

from __future__ import annotations

import re
from typing import Any

from app.services.docgen.structured.helpers import PLACEHOLDER, today_cn
from app.services.docgen.structured.schemas import STRUCTURED_FIELD_SCHEMAS

# 各类型长文/关键字段（用于补全与校验）
DOC_LONG_TEXT_FIELDS: dict[str, list[str]] = {
    "application": ["requests", "facts", "legal_basis", "evidence"],
    "labor_supervision": ["items", "facts", "evidence", "relief"],
    "complaint": ["claims", "facts", "evidence", "arbitration_info"],
    "answer": ["defense_points", "facts"],
    "appeal": ["appeal_requests", "reasons"],
    "wage_demand_letter": ["employment", "arrears"],
    "forced_termination_notice": ["facts", "article38_reasons"],
    "lawyer_letter": ["facts", "demands"],
    "legal_opinion": ["background", "analysis", "opinion"],
    "agency_opinion": ["facts_opinion", "law_opinion", "focus", "conclusion"],
    "labor_contract": ["job_duties", "wage_standard"],
    "mediation": ["dispute_summary", "payment"],
    "settlement_agreement": ["settlement_amount", "mutual_release"],
}

DOC_REQUIRED_FIELDS: dict[str, list[str]] = {
    "application": [
        "applicant_name",
        "respondent_name",
        "requests",
        "facts",
    ],
    "labor_supervision": ["complainant_name", "employer_name", "items", "facts"],
    "complaint": ["plaintiff_name", "defendant_name", "claims", "facts"],
    "wage_demand_letter": ["employer_name", "arrears"],
    "evidence_list": ["submitter", "items"],
}

# 套装生成时跨文书共享的字段
BUNDLE_SHARED_KEYS = frozenset({
    "applicant_name",
    "applicant_id",
    "applicant_address",
    "applicant_phone",
    "respondent_name",
    "respondent_address",
    "respondent_legal_rep",
    "plaintiff_name",
    "plaintiff_id",
    "plaintiff_address",
    "plaintiff_phone",
    "defendant_name",
    "defendant_address",
    "defendant_legal_rep",
    "complainant_name",
    "complainant_id",
    "complainant_phone",
    "employer_name",
    "employer_address",
    "employer_rep",
    "party_worker",
    "party_employer",
    "worker",
    "employer",
    "principal",
    "recipient",
    "requests",
    "claims",
    "facts",
    "evidence",
    "items",
    "sign_date",
})


def is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        s = v.strip()
        return not s or s == PLACEHOLDER
    return not v


def extract_shared_bundle_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in payload.items()
        if k in BUNDLE_SHARED_KEYS and not is_empty_value(v)
    }


def _infer_arbitration_commission(case_facts: str, parsed_case: dict[str, Any]) -> str:
    text = case_facts or ""
    jurisdiction = (parsed_case or {}).get("jurisdiction") or ""
    combined = f"{text} {jurisdiction}"
    m = re.search(
        r"([\u4e00-\u9fff]{2,20}?(?:市|区|县)[\u4e00-\u9fff]{0,15}?劳动人事争议仲裁委员会)",
        combined,
    )
    if m:
        return m.group(1)
    m2 = re.search(r"([\u4e00-\u9fff]{2,10}?)(?:市|区|县)", combined)
    if m2:
        return f"{m2.group(1)}市劳动人事争议仲裁委员会"
    return ""


def _infer_court(case_facts: str, parsed_case: dict[str, Any]) -> str:
    jurisdiction = (parsed_case or {}).get("jurisdiction") or ""
    if jurisdiction and "法院" in jurisdiction:
        return jurisdiction
    text = case_facts or ""
    m = re.search(r"([\u4e00-\u9fff]{2,25}?人民法院)", text)
    return m.group(1) if m else ""


def enrich_structured_payload(
    doc_type: str,
    payload: dict[str, Any],
    *,
    case_facts: str = "",
    parsed_case: dict[str, Any] | None = None,
    legal_basis_section: str = "",
    research_context: str | None = None,
) -> dict[str, Any]:
    """在渲染前补全 payload，减少 [待填写] 与空节。"""
    parsed_case = parsed_case or {}
    out = dict(payload)

    summary = (parsed_case.get("facts_summary") or "").strip()
    if summary:
        if is_empty_value(out.get("facts")):
            out["facts"] = summary
        if doc_type == "labor_supervision" and is_empty_value(out.get("items")):
            out["items"] = summary[:500]
        if doc_type == "legal_opinion" and is_empty_value(out.get("background")):
            out["background"] = summary

    if legal_basis_section and doc_type == "application":
        plain = legal_basis_section.replace("## 法律依据参考", "").strip()
        if plain and is_empty_value(out.get("legal_basis")):
            out["legal_basis"] = plain[:4000]

    if doc_type == "application":
        if is_empty_value(out.get("arbitration_commission")):
            inferred = _infer_arbitration_commission(case_facts, parsed_case)
            if inferred:
                out["arbitration_commission"] = inferred
    if doc_type in ("complaint", "answer", "appeal", "preservation_application"):
        if is_empty_value(out.get("court_name")):
            court = _infer_court(case_facts, parsed_case)
            if court:
                out["court_name"] = court

    if is_empty_value(out.get("sign_date")):
        out["sign_date"] = today_cn()

    # 研究摘要补充法律依据分析类字段（截断）
    if research_context and doc_type in ("legal_opinion", "application"):
        snippet = research_context.strip()[:2000]
        if doc_type == "legal_opinion" and is_empty_value(out.get("analysis")):
            out["analysis"] = snippet
        if doc_type == "application" and is_empty_value(out.get("legal_basis")):
            out["legal_basis"] = snippet[:1500]

    # 证据：从 parsed_case 合并
    ev = parsed_case.get("evidence_summary")
    if ev and is_empty_value(out.get("evidence")):
        out["evidence"] = "\n".join(ev) if isinstance(ev, list) else str(ev)
    if ev and doc_type == "evidence_list" and is_empty_value(out.get("items")):
        out["items"] = out.get("evidence") or (
            "\n".join(ev) if isinstance(ev, list) else str(ev)
        )

    return out


def list_missing_required(doc_type: str, payload: dict[str, Any]) -> list[str]:
    required = DOC_REQUIRED_FIELDS.get(doc_type, [])
    missing = []
    for key in required:
        if is_empty_value(payload.get(key)):
            missing.append(key)
    return missing


def list_weak_long_fields(doc_type: str, payload: dict[str, Any], min_len: int = 40) -> list[str]:
    """长文本过短或仍为占位，需二次生成。"""
    weak = []
    for key in DOC_LONG_TEXT_FIELDS.get(doc_type, []):
        v = payload.get(key)
        if is_empty_value(v):
            weak.append(key)
        elif isinstance(v, str) and len(v.strip()) < min_len and key in ("facts", "legal_basis", "claims", "requests"):
            weak.append(key)
    return weak


def field_labels_for_prompt(doc_type: str, keys: list[str]) -> str:
    schema = STRUCTURED_FIELD_SCHEMAS.get(doc_type, {})
    lines = []
    for k in keys:
        lines.append(f'  "{k}": ""  // {schema.get(k, k)}')
    return "{\n" + "\n".join(lines) + "\n}"
