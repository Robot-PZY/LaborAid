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


# Markdown 格式残留模式（需要清理）
_MD_PATTERNS = [
    (re.compile(r"^\s*[-\*]\s+", re.MULTILINE), ""),       # 列表项前缀 "- " 或 "* "
    (re.compile(r"^\s*\d+[.、)]\s*", re.MULTILINE), ""),    # 编号列表 "1. " 或 "1、"
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),                   # 加粗 **text**
    (re.compile(r"__(.+?)__"), r"\1"),                       # 加粗 __text__
    (re.compile(r"\*(.+?)\*"), r"\1"),                       # 斜体 *text*
    (re.compile(r"_(.+?)_"), r"\1"),                         # 斜体 _text_
    (re.compile(r"`(.+?)`"), r"\1"),                         # 代码 `text`
    (re.compile(r"#{1,6}\s+"), ""),                          # 标题 # text
    (re.compile(r"\[([^\]]+)\]\([^\)]+\)"), r"\1"),          # 链接 [text](url)
    (re.compile(r"^>\s+", re.MULTILINE), ""),                # 引用 > text
    (re.compile(r"^---+\s*$", re.MULTILINE), ""),            # 分隔线
    (re.compile(r"^\|.*\|\s*$", re.MULTILINE), ""),          # 表格行
]

# 需要清理 markdown 残留的字段（长文本字段）
_PAYLOAD_MD_CLEAN_FIELDS = frozenset({
    "facts", "facts_employment", "facts_dispute", "employment_info",
    "employment_background", "legal_analysis", "legal_basis",
    "dispute_details", "legal_analysis_expansion",
    "requests", "claims", "items", "relief",
    "arrears", "defense_points", "reasons", "appeal_requests",
    "background", "analysis", "opinion",
    "facts_opinion", "law_opinion", "focus", "conclusion",
    "demands", "consequences",
})


def _clean_markdown_from_payload(out: dict[str, Any]) -> None:
    """清理 payload 各字段中的 markdown 格式残留，防止泄露到文书中。"""
    for key, val in list(out.items()):
        if key not in _PAYLOAD_MD_CLEAN_FIELDS:
            continue
        if not isinstance(val, str):
            continue
        cleaned = val
        for pattern, replacement in _MD_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        # 清理多余空行
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # 清理行首行尾多余空格
        cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
        cleaned = cleaned.strip()
        if cleaned != val:
            out[key] = cleaned


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

    # 清理 payload 中的 markdown 格式残留（防止原始 markdown 泄露到文书中）
    _clean_markdown_from_payload(out)

    # --- 模板变量补全：从案情摘要中提取简单变量 ---
    _fill_template_variables_from_summary(out, summary, doc_type)

    # --- 从 parsed_case 交叉填充模板变量 ---
    _fill_template_vars_from_parsed_case(out, parsed_case, summary)

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

    # 证据隔离：证据仅用于 evidence_list 文书类型，不填充到其他文书
    # 证据是辅助 AI 认定事实的材料，不应出现在仲裁申请书/起诉状正文中
    if doc_type == "evidence_list":
        ev = parsed_case.get("evidence_summary")
        if ev and is_empty_value(out.get("items")):
            out["items"] = "\n".join(ev) if isinstance(ev, list) else str(ev)
        # evidence_list 类型也需要 submitter 和 case_ref
        if is_empty_value(out.get("submitter")):
            parties = parsed_case.get("parties", {})
            plaintiff = parties.get("plaintiff", {})
            if plaintiff.get("name"):
                out["submitter"] = plaintiff["name"]
    # 非证据类文书：清除证据相关字段，防止泄露到正文
    else:
        out.pop("evidence", None)
        out.pop("evidence_text", None)

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


def _fill_template_vars_from_parsed_case(
    out: dict[str, Any],
    parsed_case: dict[str, Any],
    summary: str,
) -> None:
    """从 parsed_case 的已有信息交叉填充模板变量。

    用户在前端填表时已经提供了很多信息（如公司名称、工作地区、行业/工种等），
    这些信息在 parsed_case 中，但之前没有被用来填充模板变量。
    """
    if not parsed_case:
        return

    # 从 parties 提取
    parties = parsed_case.get("parties") or {}
    defendant = parties.get("defendant") or {}
    plaintiff = parties.get("plaintiff") or {}

    # 被申请人名称 → 模板变量
    if defendant.get("name") and is_empty_value(out.get("respondent_name")):
        out["respondent_name"] = defendant["name"]

    # 申请人姓名 → 模板变量
    if plaintiff.get("name") and is_empty_value(out.get("applicant_name")):
        out["applicant_name"] = plaintiff["name"]

    # 从 parsed_case 顶层字段提取
    # 工作地区 → work_location
    work_area = parsed_case.get("work_area") or parsed_case.get("work_location") or ""
    if work_area and is_empty_value(out.get("work_location")):
        out["work_location"] = work_area

    # 行业/工种 → job_position
    industry = parsed_case.get("industry") or parsed_case.get("job_type") or ""
    if industry and is_empty_value(out.get("job_position")):
        out["job_position"] = industry

    # 案由 → 推断争议类型
    cause = parsed_case.get("cause_of_action") or parsed_case.get("sub_type") or ""
    if cause and is_empty_value(out.get("dispute_details")):
        # 根据案由推断争议类型，用于后续 LLM 生成 dispute_details
        out["_inferred_dispute_type"] = cause

    # 从 claims 推断金额
    claims = parsed_case.get("claims")
    if claims:
        claims_text = claims if isinstance(claims, str) else "\n".join(str(c) for c in claims)
        # 从诉求中提取金额
        if is_empty_value(out.get("arrears_amount")):
            m = re.search(r"(?:支付|给付|偿还|补发)[^0-9]{0,20}(?:工资|报酬|薪资|劳务费)[^0-9]{0,10}(\d+(?:\.\d+)?)\s*元", claims_text)
            if m:
                out["arrears_amount"] = m.group(1)
        if is_empty_value(out.get("severance_pay")):
            m = re.search(r"(?:经济补偿[金赔偿]*|赔偿金)[^0-9]{0,10}(\d+(?:\.\d+)?)\s*元", claims_text)
            if m:
                out["severance_pay"] = m.group(1)

    # 从 facts_summary 补充（如果 summary 为空但 parsed_case 有 facts_summary）
    facts_summary = parsed_case.get("facts_summary") or ""
    if facts_summary and not summary:
        # 用 facts_summary 再跑一次提取
        _fill_template_variables_from_summary(out, facts_summary, "application")


def _extract_form_fields(out: dict[str, Any], text: str) -> None:
    """从表单式输入中提取结构化字段（如"工作地区：江苏省南京市"）。

    用户在前端填写的案情描述通常是"字段名：值"的格式，
    这些 regex 专门匹配这种格式。
    """
    if not text:
        return

    # 工作地区（如"工作地区：江苏省南京市"）
    if is_empty_value(out.get("work_location")):
        m = re.search(r"工作地区[：:]\s*([\u4e00-\u9fff]{2,30})", text)
        if m:
            out["work_location"] = m.group(1).strip()

    # 行业/工种（如"行业/工种：建筑工地钢筋工"）
    if is_empty_value(out.get("job_position")):
        m = re.search(r"(?:行业|工种)[/／]?(?:工种)?[：:]\s*([\u4e00-\u9fff]{2,20})", text)
        if m:
            candidate = m.group(1).strip()
            if len(candidate) >= 2 and candidate not in ("工作", "劳动", "单位", "公司", "企业", "建筑"):
                out["job_position"] = candidate

    # 用人单位/公司名称（如"用人单位 / 包工头名称：华城建设劳务有限公司"）
    if is_empty_value(out.get("respondent_name")):
        m = re.search(r"(?:用人单位|公司名称|用人单位\s*/\s*包工头名称|公司名称\s*/\s*包工头)[：:]\s*([\u4e00-\u9fff]{2,50}?(?=[（(]|\s|$))", text)
        if m:
            out["respondent_name"] = m.group(1).strip()

    # 欠薪金额（如"欠薪金额（元）：24000"）
    if is_empty_value(out.get("arrears_amount")):
        m = re.search(r"欠薪金额[（(]元[）)][：:]\s*(\d+(?:\.\d+)?)", text)
        if m:
            out["arrears_amount"] = m.group(1)
        else:
            m2 = re.search(r"欠薪金额[：:]\s*(\d+(?:\.\d+)?)", text)
            if m2:
                out["arrears_amount"] = m2.group(1)

    # 欠薪时段（如"欠薪时段：2026年1月至2026年3月"）
    if is_empty_value(out.get("dispute_start")):
        m = re.search(r"欠薪时段[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月", text)
        if m:
            out["dispute_start"] = f"{m.group(1)}年{int(m.group(2))}月"
    if is_empty_value(out.get("dispute_end")):
        m = re.search(r"欠薪时段[：:]\s*\d{4}\s*年\s*\d{1,2}\s*月\s*至\s*(\d{4})\s*年\s*(\d{1,2})\s*月", text)
        if m:
            out["dispute_end"] = f"{m.group(1)}年{int(m.group(2))}月"

    # 月工资（从"应发(元)"或表格中提取）
    if is_empty_value(out.get("monthly_salary")):
        m = re.search(r"应发[（(]元[）)][：:]\s*(\d+(?:\.\d+)?)", text)
        if m:
            out["monthly_salary"] = m.group(1)

    # 申请人/劳动者姓名（如"姓名：李强"）
    if is_empty_value(out.get("applicant_name")):
        m = re.search(r"(?:姓名|劳动者姓名|申请人姓名)[：:]\s*([\u4e00-\u9fff]{2,4})", text)
        if m:
            out["applicant_name"] = m.group(1).strip()

    # 联系电话
    if is_empty_value(out.get("applicant_phone")):
        m = re.search(r"(?:联系方式|联系电话|电话|手机)[：:]\s*(\d{3}[\d\*]{4}\d{4})", text)
        if m:
            out["applicant_phone"] = m.group(1)

    # 出生年份
    if is_empty_value(out.get("hire_year")):
        m = re.search(r"出生年份[：:]\s*(\d{4})", text)
        if m:
            out["hire_year"] = m.group(1)


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

    # 优先从表单式字段提取（匹配"字段名：值"格式）
    _extract_form_fields(out, summary)

    # 提取入职年份（如"2023年3月入职"、"2023年入职"、"于2023年开始工作"）
    if is_empty_value(out.get("hire_year")):
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月.*?(?:入职|开始工作|进入|到.*?工作|上岗)", summary)
        if m:
            out["hire_year"] = m.group(1)
            if is_empty_value(out.get("hire_month")):
                out["hire_month"] = str(int(m.group(2)))
        else:
            m2 = re.search(r"(\d{4})\s*年.*?(?:入职|开始工作|进入.*?工作|上岗|来到.*?工作)", summary)
            if m2:
                out["hire_year"] = m2.group(1)

    # 提取入职月份（独立匹配）
    if is_empty_value(out.get("hire_month")):
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", summary)
        if m:
            out["hire_month"] = str(int(m.group(2)))

    # 提取月工资（多种写法）
    if is_empty_value(out.get("monthly_salary")):
        patterns = [
            r"(?:月工资|月薪|工资标准|基本工资|约定工资|每月工资)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*元",
            r"(?:工资|薪水)[^0-9]{0,10}(\d+(?:\.\d+)?)\s*元/月",
            r"(\d+(?:\.\d+)?)\s*元/月",
            r"(\d+(?:\.\d+)?)\s*元\s*每月",
            r"每月\s*(\d+(?:\.\d+)?)\s*元",
            r"月\s*(\d+(?:\.\d+)?)\s*(?:块|元)",
            # 从表格行提取（如"2026-01 8000.00 0.00 未发放"）
            r"\d{4}[-/]\d{2}\s+(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?\s+未发放",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                out["monthly_salary"] = m.group(1)
                break

    # 提取欠薪/欠款金额（多种写法）
    if is_empty_value(out.get("arrears_amount")):
        patterns = [
            r"(?:拖欠|欠薪|欠款|欠付|未支付|未发放|未结清)[^0-9]{0,20}(?:工资|报酬|薪资|薪酬|劳务费)[^0-9]{0,10}(\d+(?:\.\d+)?)\s*元",
            r"(?:拖欠|欠薪|欠款|欠付|未支付|未发放)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*元",
            r"(?:共计|累计|合计|总共)[^0-9]{0,10}(?:拖欠|欠|未付)[^0-9]{0,10}(\d+(?:\.\d+)?)\s*元",
            r"(?:工资|报酬)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*元[^0-9]{0,20}(?:未付|未发|拖欠|欠)",
            r"(\d+(?:\.\d+)?)\s*元[^0-9]{0,20}(?:未付|未发|拖欠|欠薪|未支付)",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                out["arrears_amount"] = m.group(1)
                break

    # 提取经济补偿金/赔偿金
    if is_empty_value(out.get("severance_pay")):
        m = re.search(r"(?:经济补偿[金赔偿]*|赔偿金|补偿金)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*元", summary)
        if m:
            out["severance_pay"] = m.group(1)

    # 提取加班费
    if is_empty_value(out.get("overtime_pay")):
        m = re.search(r"(?:加班费|加班工资|加班报酬)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*元", summary)
        if m:
            out["overtime_pay"] = m.group(1)

    # 提取欠薪时间范围（多种写法）
    if is_empty_value(out.get("dispute_start")):
        patterns = [
            r"(\d{4})\s*年\s*(\d{1,2})\s*月.*?(?:至|到|起至|期间)",
            r"(?:自|从)(\d{4})\s*年\s*(\d{1,2})\s*月",
            r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:起|开始)",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                out["dispute_start"] = f"{m.group(1)}年{int(m.group(2))}月"
                break
    if is_empty_value(out.get("dispute_end")):
        patterns = [
            r"(?:至|到)\s*(\d{4})\s*年\s*(\d{1,2})\s*月",
            r"(?:截至|截止)(\d{4})\s*年\s*(\d{1,2})\s*月",
            r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:止|结束|底)",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                out["dispute_end"] = f"{m.group(1)}年{int(m.group(2))}月"
                break

    # 提取工作地点（多种写法）
    if is_empty_value(out.get("work_location")):
        patterns = [
            r"(?:工作地点|工作地|上班地点|上班地|工作场所|工地)[^，。]{0,20}([\u4e00-\u9fff]{2,30}(?:市|区|县|镇))",
            r"在([\u4e00-\u9fff]{2,30}(?:市|区|县|镇))[^，。]{0,10}(?:工作|上班|务工|打工|干活)",
            r"(?:位于|地处)([\u4e00-\u9fff]{2,30}(?:市|区|县|镇))",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                out["work_location"] = m.group(1)
                break

    # 提取岗位（多种写法）
    if is_empty_value(out.get("job_position")):
        patterns = [
            r"(?:担任|岗位[为是]|从事|做|工种[为是]|职位[为是])([\u4e00-\u9fff]{2,10})(?:岗位|工作|职务)?",
            r"([\u4e00-\u9fff]{2,10})(?:工|员|师|长)",
        ]
        for pat in patterns:
            m = re.search(pat, summary)
            if m:
                candidate = m.group(1)
                # 过滤掉太短或明显不是岗位的词
                if len(candidate) >= 2 and candidate not in ("工作", "劳动", "单位", "公司", "企业", "建筑"):
                    out["job_position"] = candidate
                    break

    # 提取合同签订情况
    if is_empty_value(out.get("contract_info")):
        if re.search(r"(?:未|没|没有).{0,10}(?:签订|签署|订立).{0,10}(?:劳动|书面)", summary):
            out["contract_info"] = "未签订书面劳动合同"
        elif re.search(r"(?:签订|签署|订立).{0,10}(?:劳动|书面)", summary):
            m = re.search(r"(?:签订|签署|订立).{0,10}(?:于|在)?\s*(\d{4})\s*年\s*(\d{1,2})\s*月", summary)
            if m:
                out["contract_info"] = f"于{m.group(1)}年{int(m.group(2))}月签订书面劳动合同"

    # 提取社保缴纳情况
    if is_empty_value(out.get("social_insurance_info")):
        if re.search(r"(?:未|没|没有).{0,10}(?:缴纳|购买|参保).{0,10}社保", summary):
            out["social_insurance_info"] = "未依法缴纳社会保险"
        elif re.search(r"(?:缴纳|购买|参保).{0,10}社保", summary):
            out["social_insurance_info"] = "已缴纳社会保险"

    # 提取仲裁机构
    if is_empty_value(out.get("arbitration_commission")):
        m = re.search(r"([\u4e00-\u9fff]{2,20}(?:市|区|县)[\u4e00-\u9fff]{0,15}?劳动人事争议仲裁委员会)", summary)
        if m:
            out["arbitration_commission"] = m.group(1)

    # 提取仲裁案号
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
