"""LLM 不可用时的规则化文书生成（保证用户总能拿到可编辑初稿）。"""

from __future__ import annotations

import re
from typing import Any

from app.services.docgen.content_sanitize import sanitize_legal_document_content
from app.services.docgen.structured.enrich import enrich_structured_payload
from app.services.docgen.structured.helpers import seed_from_parsed_case, today_cn, clean_case_facts_narrative, _default_labor_evidence_items
from app.services.docgen.structured.renderers import render_structured_document
from app.services.docgen.title_format import format_case_document_title
from app.services.docgen.types import normalize_doc_type
from app.services.docgen.prompts import DOC_TYPE_NAMES


def _extract_evidence_items(case_facts: str) -> str:
    """从案情中提取证据条目；若无明确证据节则返回空。"""
    text = (case_facts or "").strip()
    if not text:
        return ""

    section = ""
    m = re.search(
        r"(?:^|\n)(?:#{1,3}\s*)?(?:证据材料|证据清单|证据目录|附件清单)[^\n]*\n((?:[\-\*•\d].+\n?)+)",
        text,
        re.MULTILINE,
    )
    if m:
        section = m.group(1)

    items: list[str] = []
    source = section or text
    for line in source.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(\d+[.、)]|证据[一二三四五六七八九十\d]+|[（(]\d+[)）])", line):
            items.append(re.sub(r"^(\d+[.、)]\s*|证据[一二三四五六七八九十\d]+[：:]\s*)", "", line))
        elif line.startswith("- ") or line.startswith("• "):
            item = line[2:].strip()
            if _is_metadata_bullet(item):
                continue
            if re.search(r"合同|通知|记录|流水|社保|工资|聊天|录音|录像|证明|协议|函|清单", item):
                items.append(item)

    if items:
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))
    return ""


def _is_metadata_bullet(item: str) -> bool:
    return bool(
        re.match(
            r"(案件编号|案由类型|争议焦点|工作地区|当前状态|目标[：:]|月薪[：:]|入职时间[：:]|解除时间[：:]|试用期[：:])",
            item,
        )
    )


def _build_default_requests(case_facts: str, parsed: dict[str, Any]) -> str:
    """根据案情生成更完整的仲裁/诉讼请求。"""
    text = (case_facts or "").strip()
    claims = parsed.get("claims") or []
    if isinstance(claims, list) and claims:
        return "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))

    lines: list[str] = []
    amount = re.search(r"(\d+(?:\.\d+)?)\s*元", text)
    if amount:
        lines.append(f"请求被申请人支付拖欠工资人民币{amount.group(1)}元")
    if re.search(r"双倍|2倍|二倍|经济补偿|赔偿金|补偿金", text):
        lines.append("请求被申请人支付违法解除劳动合同赔偿金（或经济补偿金）")
    if re.search(r"未签.*劳动合同|没有.*劳动合同", text):
        lines.append("请求被申请人支付未订立书面劳动合同的二倍工资差额")
    if re.search(r"社保|社会保险", text):
        lines.append("请求被申请人补缴社会保险或赔偿相应损失")
    if re.search(r"试用期|录用条件|不符合录用", text):
        lines.append("确认被申请人违法解除/终止劳动合同")
        lines.append("请求被申请人支付违法解除劳动合同赔偿金")
    if not lines:
        lines.append("请求被申请人支付拖欠劳动报酬及相关费用")
    lines.append("本案仲裁费用由被申请人承担")
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


def rule_parse_case(case_facts: str) -> dict[str, Any]:
    """从案情文本规则提取当事人，不调用 LLM。"""
    text = (case_facts or "").strip()
    parties: dict[str, Any] = {"plaintiff": {}, "defendant": {}}

    for pattern, role, field in [
        (r"原告[：:\s]*([^\n，,。；;]{2,30})", "plaintiff", "name"),
        (r"申请人[：:\s]*([^\n，,。；;]{2,30})", "plaintiff", "name"),
        (r"劳动者[：:\s]*([^\n，,。；;]{2,20})", "plaintiff", "name"),
        (r"员工[：:\s]*([^\n，,。；;]{2,20})", "plaintiff", "name"),
        (r"被告[：:\s]*([^\n，,。；;]{2,30})", "defendant", "name"),
        (r"被申请人[：:\s]*([^\n，,。；;]{2,30})", "defendant", "name"),
        (r"用人单位[^：:]*[：:\s]*([^\n，,。；;]{2,40})", "defendant", "name"),
        (r"公司[：:\s]*([^\n，,。；;]{2,40})", "defendant", "name"),
        (r"包工头[：:\s]*([^\n，,。；;]{2,20})", "defendant", "name"),
    ]:
        m = re.search(pattern, text)
        if m and field == "name":
            val = m.group(1).strip()
            if val and not parties[role].get("name"):
                parties[role]["name"] = val

    evidence_items = _extract_evidence_items(text)
    evidence_summary = evidence_items or _default_labor_evidence_items(text)

    narrative = clean_case_facts_narrative(text) or text

    return {
        "case_type": "劳动争议",
        "cause_of_action": "劳动争议",
        "facts": narrative,
        "facts_summary": narrative[:800] if len(narrative) > 800 else narrative,
        "claims": [ln.split(". ", 1)[-1] for ln in _build_default_requests(text, {}).splitlines()],
        "parties": parties,
        "evidence_summary": evidence_summary,
    }


def build_offline_structured_document(
    *,
    doc_type: str,
    case_facts: str,
    parsed_case: dict[str, Any] | None = None,
    case_title: str | None = None,
) -> dict[str, Any]:
    """规则填充 + 固定模板渲染，不调用 LLM。"""
    canonical = normalize_doc_type(doc_type) or doc_type
    doc_type_name = DOC_TYPE_NAMES.get(canonical, canonical)
    parsed = parsed_case or rule_parse_case(case_facts)
    seed = seed_from_parsed_case(parsed)
    if not seed.get("facts"):
        seed["facts"] = clean_case_facts_narrative(case_facts) or (case_facts or "").strip()
    if not seed.get("requests"):
        seed["requests"] = _build_default_requests(case_facts, parsed)
    if canonical == "forced_termination_notice" and not seed.get("article38_reasons"):
        seed["article38_reasons"] = (
            "用人单位未依法提供劳动条件/未及时足额支付劳动报酬/违法规章制度等情形"
            "（请据实勾选第38条具体项并补充事实）"
        )
    if canonical == "evidence_list":
        ev_items = _extract_evidence_items(case_facts) or _default_labor_evidence_items(case_facts)
        if ev_items:
            seed["items"] = ev_items
    seed["sign_date"] = seed.get("sign_date") or today_cn()

    payload = enrich_structured_payload(
        canonical,
        seed,
        case_facts=case_facts,
        parsed_case=parsed,
        legal_basis_section="",
        research_context=None,
    )
    content = render_structured_document(canonical, payload)
    content = sanitize_legal_document_content(content, doc_type_name)

    plaintiff = (parsed.get("parties") or {}).get("plaintiff", {}).get("name", "")
    defendant = (parsed.get("parties") or {}).get("defendant", {}).get("name", "")
    title = format_case_document_title(
        case_title=case_title,
        doc_type_label=doc_type_name,
        plaintiff=plaintiff,
        defendant=defendant,
    )

    return {
        "title": title,
        "content": content,
        "metadata": {
            "parsed_case": parsed,
            "generation_mode": "offline_fallback",
            "structured_payload": payload,
        },
    }
