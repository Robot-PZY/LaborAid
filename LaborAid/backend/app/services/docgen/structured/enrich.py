"""结构化 payload 后处理：案情补全、研究摘要、仲裁委推断等。"""

from __future__ import annotations

import re
from typing import Any

from app.services.docgen.structured.helpers import PLACEHOLDER, today_cn, clean_case_facts_narrative, _default_labor_evidence_items
from app.services.docgen.structured.schemas import STRUCTURED_FIELD_SCHEMAS

# 各类型长文/关键字段（用于补全与校验）
DOC_LONG_TEXT_FIELDS: dict[str, list[str]] = {
    "application": [
        "requests", "facts", "facts_employment", "facts_dispute",
        "employment_info", "legal_analysis", "legal_basis", "evidence",
        "dispute_details", "legal_analysis_expansion",  # 模板变量
    ],
    "labor_supervision": [
        "items", "facts", "employment_info", "evidence", "relief",
        "dispute_details",  # 模板变量
    ],
    "complaint": [
        "claims", "facts", "facts_arbitration", "facts_dispute",
        "employment_background", "legal_analysis", "evidence", "arbitration_info",
        "dispute_details", "legal_analysis_expansion",  # 模板变量
    ],
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
        "facts_dispute",
        "legal_basis",
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
    "respondent_usci",
    "plaintiff_name",
    "plaintiff_id",
    "plaintiff_address",
    "plaintiff_phone",
    "defendant_name",
    "defendant_address",
    "defendant_legal_rep",
    "defendant_usci",
    "complainant_name",
    "complainant_id",
    "complainant_phone",
    "complainant_address",
    "employer_name",
    "employer_address",
    "employer_rep",
    "employer_legal_rep",
    "party_worker",
    "party_employer",
    "worker",
    "employer",
    "principal",
    "recipient",
    "requests",
    "claims",
    "facts",
    "facts_employment",
    "facts_dispute",
    "employment_info",
    "employment_background",
    "legal_analysis",
    "legal_basis",
    "evidence",
    "items",
    "sign_date",
    # 模板变量
    "hire_year", "hire_month", "job_position", "monthly_salary",
    "monthly_salary_cn", "contract_info", "work_location",
    "social_insurance_info", "dispute_start", "dispute_end",
    "arrears_amount", "arrears_amount_cn", "dispute_details",
    "legal_analysis_expansion",
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


_DEFAULT_LEGAL_BASIS = (
    "依据《中华人民共和国劳动争议调解仲裁法》第二条、第五条，"
    "《中华人民共和国劳动合同法》第三十八条、第四十六条、第四十七条、第八十七条等规定，"
    "用人单位应当向劳动者承担相应法律责任。"
)


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

    summary = (parsed_case.get("facts_summary") or parsed_case.get("facts") or "").strip()
    cf = clean_case_facts_narrative(case_facts or "") or (case_facts or "").strip()
    if not summary and cf:
        summary = cf[:3000]

    # --- 模板变量补全：从案情摘要中提取简单变量 ---
    _fill_template_variables_from_summary(out, summary, doc_type)

    # --- 新子字段与 facts 之间的互补逻辑 ---
    if doc_type == "application":
        _cross_fill_facts_subfields(out, summary, sub_fields=["facts_employment", "facts_dispute"])
    elif doc_type == "complaint":
        _cross_fill_facts_subfields(out, summary, sub_fields=["employment_background", "facts_arbitration", "facts_dispute"])

    if summary:
        if is_empty_value(out.get("facts")):
            out["facts"] = summary if len(summary) <= 4000 else summary[:4000]
        if doc_type == "labor_supervision":
            if is_empty_value(out.get("items")):
                out["items"] = summary[:800]
            if is_empty_value(out.get("employment_info")):
                out["employment_info"] = summary[:600]
        if doc_type == "legal_opinion" and is_empty_value(out.get("background")):
            out["background"] = summary[:2000]
        if doc_type == "forced_termination_notice" and is_empty_value(out.get("facts")):
            out["facts"] = summary[:3000]

    if legal_basis_section and doc_type in ("application", "complaint"):
        plain = legal_basis_section.replace("## 法律依据参考", "").strip()
        if plain and is_empty_value(out.get("legal_basis")):
            out["legal_basis"] = plain[:4000]
        if plain and doc_type == "complaint" and is_empty_value(out.get("legal_analysis")):
            out["legal_analysis"] = plain[:3000]

    if doc_type == "application":
        if is_empty_value(out.get("arbitration_commission")):
            inferred = _infer_arbitration_commission(case_facts, parsed_case)
            if inferred:
                out["arbitration_commission"] = inferred
        if is_empty_value(out.get("legal_basis")):
            out["legal_basis"] = _DEFAULT_LEGAL_BASIS
    if doc_type in ("complaint", "answer", "appeal", "preservation_application"):
        if is_empty_value(out.get("court_name")):
            court = _infer_court(case_facts, parsed_case)
            if court:
                out["court_name"] = court

    if is_empty_value(out.get("sign_date")):
        out["sign_date"] = today_cn()

    # 研究摘要补充法律依据分析类字段（截断）
    if research_context and doc_type in ("legal_opinion", "application", "complaint"):
        snippet = research_context.strip()[:2000]
        if doc_type == "legal_opinion" and is_empty_value(out.get("analysis")):
            out["analysis"] = snippet
        if doc_type in ("application", "complaint") and is_empty_value(out.get("legal_basis")):
            out["legal_basis"] = snippet[:1500]
        if doc_type == "complaint" and is_empty_value(out.get("legal_analysis")):
            out["legal_analysis"] = snippet[:1500]

    # 证据：从 parsed_case 合并
    ev = parsed_case.get("evidence_summary")
    if ev and is_empty_value(out.get("evidence")):
        out["evidence"] = "\n".join(ev) if isinstance(ev, list) else str(ev)
    if ev and doc_type == "evidence_list" and is_empty_value(out.get("items")):
        out["items"] = out.get("evidence") or (
            "\n".join(ev) if isinstance(ev, list) else str(ev)
        )
    if doc_type in ("application", "complaint", "forced_termination_notice") and is_empty_value(out.get("evidence")):
        out["evidence"] = _default_labor_evidence_items(case_facts)

    return out


def _cross_fill_facts_subfields(
    out: dict[str, Any],
    summary: str,
    *,
    sub_fields: list[str],
) -> None:
    """子字段与 facts 之间的互补填充。

    - 如果子字段有内容但 facts 为空 → 合并子字段到 facts
    - 如果 facts 有内容但子字段为空 → 将 summary 填充到第一个空缺子字段
    """
    facts_val = out.get("facts", "")
    has_facts = not is_empty_value(facts_val)

    sub_vals = {k: out.get(k, "") for k in sub_fields}
    filled_subs = [k for k, v in sub_vals.items() if not is_empty_value(v)]
    empty_subs = [k for k, v in sub_vals.items() if is_empty_value(v)]

    # 子字段有内容但 facts 为空 → 合并到 facts
    if filled_subs and not has_facts:
        merged_parts = []
        for k in sub_fields:
            v = sub_vals[k]
            if not is_empty_value(v):
                merged_parts.append(str(v).strip())
        if merged_parts:
            out["facts"] = "\n\n".join(merged_parts)

    # facts 有内容但子字段全空 → 用 summary 填充第一个子字段
    elif has_facts and not filled_subs and empty_subs and summary:
        out[empty_subs[0]] = summary[:2000] if len(summary) > 2000 else summary


def _fill_template_variables_from_summary(
    out: dict[str, Any],
    summary: str,
    doc_type: str,
) -> None:
    """从案情摘要中用正则提取简单的模板变量（日期、金额等），填充空缺字段。

    只提取确定性高的结构化信息（年份、月份、金额），
    不提取需要 LLM 理解的长文本字段（如 dispute_details）。
    """
    if not summary:
        return

    # 提取入职年份（如"2023年3月入职"）
    if is_empty_value(out.get("hire_year")):
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月.*?入职", summary)
        if m:
            out["hire_year"] = m.group(1)
            if is_empty_value(out.get("hire_month")):
                out["hire_month"] = str(int(m.group(2)))

    # 提取入职月份（独立匹配）
    if is_empty_value(out.get("hire_month")):
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", summary)
        if m:
            out["hire_month"] = str(int(m.group(2)))

    # 提取月工资（如"月工资8000元"、"月薪8000"）
    if is_empty_value(out.get("monthly_salary")):
        m = re.search(r"(?:月工资|月薪|工资标准)[^0-9]*(\d+(?:\.\d+)?)\s*元", summary)
        if m:
            out["monthly_salary"] = m.group(1)

    # 提取欠薪金额（如"拖欠工资24000元"、"欠薪24000"）
    if is_empty_value(out.get("arrears_amount")):
        m = re.search(r"(?:拖欠|欠薪|欠款|欠付)[^0-9]*(\d+(?:\.\d+)?)\s*元", summary)
        if m:
            out["arrears_amount"] = m.group(1)

    # 提取欠薪时间范围（如"2026年1月至2026年3月"）
    if is_empty_value(out.get("dispute_start")):
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月.*?至", summary)
        if m:
            out["dispute_start"] = f"{m.group(1)}年{int(m.group(2))}月"
    if is_empty_value(out.get("dispute_end")):
        m = re.search(r"至\s*(\d{4})\s*年\s*(\d{1,2})\s*月", summary)
        if m:
            out["dispute_end"] = f"{m.group(1)}年{int(m.group(2))}月"

    # 提取工作地点（如"工作地点位于江苏省南京市"）
    if is_empty_value(out.get("work_location")):
        m = re.search(r"(?:工作地点|工作地|上班地点)[^，。]*?([\u4e00-\u9fff]{2,30}(?:市|区|县|镇))", summary)
        if m:
            out["work_location"] = m.group(1)

    # 提取岗位（如"担任钢筋工岗位"、"岗位为保洁员"）
    if is_empty_value(out.get("job_position")):
        m = re.search(r"(?:担任|岗位[为是])([\u4e00-\u9fff]{2,10})(?:岗位|工作)", summary)
        if m:
            out["job_position"] = m.group(1)

    # 提取仲裁机构（如"向南京市劳动人事争议仲裁委员会申请"）
    if doc_type == "complaint" and is_empty_value(out.get("arbitration_commission")):
        m = re.search(r"([\u4e00-\u9fff]{2,20}(?:市|区|县)[\u4e00-\u9fff]{0,15}?劳动人事争议仲裁委员会)", summary)
        if m:
            out["arbitration_commission"] = m.group(1)

    # 提取仲裁案号（如"(2025)宁劳人仲案字第123号"）
    if doc_type == "complaint" and is_empty_value(out.get("arbitration_case_number")):
        m = re.search(r"[(（]\d{4}[)）][\u4e00-\u9fff]*劳人仲[案裁]字第?\s*(\d+)\s*号", summary)
        if m:
            out["arbitration_case_number"] = f"({m.group(0)[:6]})...第{m.group(1)}号"


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
    # 需要检查最低长度的关键字段（含新增子字段和模板变量）
    _MIN_LEN_KEYS = {
        "facts", "facts_employment", "facts_dispute", "employment_info",
        "employment_background", "legal_analysis", "legal_basis",
        "claims", "requests", "arbitration_info",
        "dispute_details", "legal_analysis_expansion",
    }
    for key in DOC_LONG_TEXT_FIELDS.get(doc_type, []):
        v = payload.get(key)
        if is_empty_value(v):
            weak.append(key)
        elif isinstance(v, str) and len(v.strip()) < min_len and key in _MIN_LEN_KEYS:
            weak.append(key)
    return weak


def field_labels_for_prompt(doc_type: str, keys: list[str]) -> str:
    schema = STRUCTURED_FIELD_SCHEMAS.get(doc_type, {})
    lines = []
    for k in keys:
        lines.append(f'  "{k}": ""  // {schema.get(k, k)}')
    return "{\n" + "\n".join(lines) + "\n}"
