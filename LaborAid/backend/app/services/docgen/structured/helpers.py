"""结构化文书渲染 — 通用 Markdown 拼装工具（参照 lawgpt json2docx 思路）。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


PLACEHOLDER = "[待填写]"


def val(data: dict[str, Any], key: str, default: str = PLACEHOLDER) -> str:
    v = data.get(key)
    if v is None:
        return default
    if isinstance(v, (list, dict)):
        return default
    s = str(v).strip()
    return s if s else default


def today_cn() -> str:
    return datetime.now().strftime("%Y年%m月%d日")


def md_title(title: str) -> str:
    return f"# {title}\n\n"


def md_section(heading: str, body: str) -> str:
    body = body.strip()
    if not body:
        body = PLACEHOLDER
    return f"## {heading}\n\n{body}\n\n"


def md_field(label: str, value: str) -> str:
    return f"**{label}**：{value}\n"


def md_fields_block(fields: list[tuple[str, str]]) -> str:
    return "".join(md_field(l, v) for l, v in fields) + "\n"


def md_numbered_list(text: str | list[str] | None) -> str:
    if text is None:
        return f"1. {PLACEHOLDER}\n"
    if isinstance(text, list):
        lines = [str(x).strip() for x in text if str(x).strip()]
    else:
        raw = str(text).strip()
        if not raw:
            return f"1. {PLACEHOLDER}\n"
        lines = []
        for part in re.split(r"\n+|(?:\d+)[.、)]\s*", raw):
            part = part.strip()
            if part:
                lines.append(part)
        if not lines:
            lines = [raw]
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1)) + "\n"


def md_paragraphs(text: str | None) -> str:
    if not text or not str(text).strip():
        return f"{PLACEHOLDER}\n"
    lines = [ln.strip() for ln in str(text).split("\n") if ln.strip()]
    return "\n".join(lines) + "\n"


def md_sign_arbitration(commission: str, signer_label: str = "申请人", date: str | None = None) -> str:
    commission = commission if commission and commission != PLACEHOLDER else "××劳动人事争议仲裁委员会"
    date = date or today_cn()
    return (
        "## 落款\n\n"
        "此致\n"
        f"{commission}\n\n"
        f"{signer_label}：[签名]\n"
        f"{date}\n"
    )


def md_sign_court(court: str, signer_label: str = "起诉人", date: str | None = None) -> str:
    court = court if court and court != PLACEHOLDER else "××人民法院"
    date = date or today_cn()
    return (
        "## 落款\n\n"
        "此致\n"
        f"{court}\n\n"
        f"附：本诉状副本×份\n\n"
        f"{signer_label}：[签名]\n"
        f"{date}\n"
    )


def md_sign_letter(recipient: str, signer: str = "劳动者", date: str | None = None) -> str:
    date = date or today_cn()
    return f"\n{signer}：[签名]\n{date}\n"


def seed_from_parsed_case(parsed_case: dict[str, Any] | None) -> dict[str, Any]:
    """从案件解析结果预填结构化字段。"""
    if not parsed_case:
        return {}
    parties = parsed_case.get("parties") or {}
    plaintiff = parties.get("plaintiff") or {}
    defendant = parties.get("defendant") or {}
    agent = parties.get("agent") or {}
    out: dict[str, Any] = {}
    if plaintiff.get("name"):
        out["applicant_name"] = plaintiff["name"]
        out["plaintiff_name"] = plaintiff["name"]
        out["complainant_name"] = plaintiff["name"]
        out["principal"] = plaintiff["name"]
        out["party_worker"] = plaintiff["name"]
        out["worker"] = plaintiff["name"]
        out["employee_name"] = plaintiff["name"]
    if plaintiff.get("identity"):
        out["applicant_id"] = plaintiff["identity"]
        out["plaintiff_id"] = plaintiff["identity"]
        out["complainant_id"] = plaintiff["identity"]
        out["employee_id"] = plaintiff["identity"]
    if plaintiff.get("address"):
        out["applicant_address"] = plaintiff["address"]
        out["plaintiff_address"] = plaintiff["address"]
        out["employee_address"] = plaintiff["address"]
    if plaintiff.get("phone"):
        out["applicant_phone"] = plaintiff["phone"]
        out["complainant_phone"] = plaintiff["phone"]
    if defendant.get("name"):
        out["respondent_name"] = defendant["name"]
        out["defendant_name"] = defendant["name"]
        out["employer_name"] = defendant["name"]
        out["party_employer"] = defendant["name"]
        out["employer"] = defendant["name"]
        out["recipient"] = defendant["name"]
        out["respondent"] = defendant["name"]
    if defendant.get("address"):
        out["respondent_address"] = defendant["address"]
        out["defendant_address"] = defendant["address"]
        out["employer_address"] = defendant["address"]
    if defendant.get("legal_rep"):
        out["respondent_legal_rep"] = defendant["legal_rep"]
        out["employer_rep"] = defendant["legal_rep"]
    if parsed_case.get("claims"):
        claims = parsed_case["claims"]
        if isinstance(claims, list):
            out["requests"] = "\n".join(str(c) for c in claims)
            out["claims"] = out["requests"]
        else:
            out["requests"] = str(claims)
            out["claims"] = str(claims)
    if parsed_case.get("facts"):
        out["facts"] = parsed_case["facts"]
    if parsed_case.get("cause_of_action"):
        out["cause_of_action"] = parsed_case["cause_of_action"]
    if parsed_case.get("jurisdiction"):
        out["court_name"] = parsed_case["jurisdiction"]
        out["court"] = parsed_case["jurisdiction"]
    if agent.get("name"):
        out["agent"] = agent["name"]
    if parsed_case.get("evidence_summary"):
        ev = parsed_case["evidence_summary"]
        if isinstance(ev, list):
            out["evidence"] = "\n".join(str(e) for e in ev)
            out["items"] = out["evidence"]
        else:
            out["evidence"] = str(ev)
    out["sign_date"] = today_cn()
    out["日期"] = today_cn()
    return out


def fallback_parse_json(text: str) -> dict[str, Any]:
    import json

    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def merge_payload(seed: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    """提取结果覆盖种子；空值保留种子或占位。"""
    merged = {**seed}
    for k, v in extracted.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (list, dict)) and not v:
            continue
        merged[k] = v
    return merged
