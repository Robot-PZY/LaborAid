"""结构化文书渲染 — 通用 Markdown 拼装（贴近真实法律文书版式）。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


PLACEHOLDER = "[待填写]"
NO_INDENT = "<!-- no-indent -->"


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


def md_cn_section(cn_num: str, title: str, body: str) -> str:
    """一级节：一、仲裁请求 — 符合仲裁/诉讼文书习惯。"""
    body = body.strip() or PLACEHOLDER
    return f"## {cn_num}、{title}\n\n{body}\n\n"


def md_sub_heading(title: str) -> str:
    """二级节：（一）劳动关系基本情况"""
    return f"### {title}\n\n"


def md_field(label: str, value: str) -> str:
    return f"**{label}**：{value}\n"


def md_fields_block(fields: list[tuple[str, str]]) -> str:
    return "".join(md_field(l, v) for l, v in fields) + "\n"


def md_party_line(role: str, fields: list[tuple[str, str]]) -> str:
    """当事人信息 — 单行紧凑，无首行缩进。"""
    segments = "，".join(f"{label}：{value}" for label, value in fields)
    return f"{NO_INDENT}**{role}**：{segments}。\n\n"


def md_salutation(addressee: str) -> str:
    """函件/通知书致送：致 XX 公司"""
    name = addressee if addressee and addressee != PLACEHOLDER else "××用人单位"
    return f"{NO_INDENT}{name}：\n\n"


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


def _split_into_paragraphs(text: str, *, max_chars: int = 280) -> list[str]:
    """长事实按句号拆成多段，便于阅读。"""
    text = text.strip()
    if not text:
        return []
    if "\n\n" in text:
        return [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]

    sentences = re.split(r"(?<=[。；！？])", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [text]

    paras: list[str] = []
    buf = ""
    for s in sentences:
        if buf and len(buf) + len(s) > max_chars:
            paras.append(buf)
            buf = s
        else:
            buf = buf + s if buf else s
    if buf:
        paras.append(buf)
    return paras


def md_body_paragraphs(text: str | None) -> str:
    """正文段落 — 首行缩进由排版引擎处理。"""
    if not text or not str(text).strip():
        return f"{PLACEHOLDER}\n"
    paras = _split_into_paragraphs(str(text))
    return "\n\n".join(paras) + "\n"


def md_paragraphs(text: str | None) -> str:
    return md_body_paragraphs(text)


def _parse_list_items(text: str | list[str] | None) -> list[str]:
    if text is None:
        return []
    if isinstance(text, list):
        return [str(x).strip() for x in text if str(x).strip()]
    raw = str(text).strip()
    if not raw:
        return []
    items: list[str] = []
    for part in re.split(r"\n+|(?:\d+)[.、)]\s*", raw):
        part = part.strip()
        if part:
            items.append(part)
    return items or [raw]


def _split_evidence_item(item: str) -> tuple[str, str]:
    """证据条目 → 名称 + 证明内容。"""
    item = item.strip()
    for sep in ("—", "－", "-", "：", ":", "，证明"):
        if sep in item:
            left, _, right = item.partition(sep)
            if right.strip():
                return left.strip(), right.strip()
    if "证明" in item:
        idx = item.find("证明")
        return item[:idx].strip("，、 "), item[idx:].strip()
    return item, "证明相关案件事实"


def md_evidence_table(items_text: str | list[str] | None) -> str:
    """证据目录表格 — 仲裁/诉讼常用四列表。"""
    items = _parse_list_items(items_text)
    if not items:
        items = [PLACEHOLDER]
    rows = [
        "| 序号 | 证据名称 | 证明内容 | 页数 |",
        "| --- | --- | --- | --- |",
    ]
    for i, item in enumerate(items, 1):
        name, purpose = _split_evidence_item(item)
        rows.append(f"| {i} | {name} | {purpose} |  |")
    return "\n".join(rows) + "\n\n"


def md_sign_arbitration(commission: str, signer_label: str = "申请人", date: str | None = None) -> str:
    commission = commission if commission and commission != PLACEHOLDER else "××劳动人事争议仲裁委员会"
    date = date or today_cn()
    return (
        f"{NO_INDENT}此致\n\n"
        f"{NO_INDENT}{commission}\n\n"
        f"{NO_INDENT}{signer_label}：（签名）\n"
        f"{NO_INDENT}{date}\n"
    )


def md_sign_court(court: str, signer_label: str = "起诉人", date: str | None = None) -> str:
    court = court if court and court != PLACEHOLDER else "××人民法院"
    date = date or today_cn()
    return (
        f"{NO_INDENT}此致\n\n"
        f"{NO_INDENT}{court}\n\n"
        f"{NO_INDENT}附：本诉状副本×份\n\n"
        f"{NO_INDENT}{signer_label}：（签名）\n"
        f"{NO_INDENT}{date}\n"
    )


def md_sign_letter(recipient: str, signer: str = "劳动者", date: str | None = None) -> str:
    date = date or today_cn()
    return (
        f"{NO_INDENT}特此通知。\n\n"
        f"{NO_INDENT}{signer}：（签名）\n"
        f"{NO_INDENT}{date}\n"
    )


def clean_case_facts_narrative(text: str) -> str:
    """将案情 Markdown/要点列表转为连贯叙述，便于写入文书正文。"""
    if not text or not str(text).strip():
        return ""
    lines_out: list[str] = []
    skip_keys = ("案件编号", "案由类型", "争议焦点", "当前状态", "目标：", "目标:")
    for line in str(text).splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.startswith("- "):
            item = s[2:].strip()
            if any(item.startswith(k) for k in skip_keys):
                continue
            if not item.endswith("。"):
                item += "。"
            lines_out.append(item)
        elif s.startswith("* "):
            item = s[2:].strip()
            if not item.endswith("。"):
                item += "。"
            lines_out.append(item)
        else:
            lines_out.append(s.rstrip("。") + "。" if s else "")
    merged = "".join(lines_out)
    merged = re.sub(r"。+", "。", merged)
    return merged.strip()


def _default_labor_evidence_items(case_facts: str) -> str:
    """无明确证据列表时，按常见劳动争议类型给出目录框架。"""
    text = case_facts or ""
    items = ["劳动合同—证明劳动关系成立"]
    if re.search(r"解除|辞退|开除|离职", text):
        items.append("解除劳动合同通知书或解除通知聊天记录—证明解除事实及理由")
    if re.search(r"工资|欠薪|报酬", text):
        items.append("工资银行流水或工资条—证明工资标准及支付情况")
    if re.search(r"社保", text):
        items.append("社会保险缴费记录—证明社保缴纳情况")
    if re.search(r"试用期|考核|录用条件", text):
        items.append("录用条件确认书、试用期考核记录—证明试用期内履职及考核情况")
    items.append("其他与本案有关的书证、电子数据—证明案件相关事实")
    return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1))


def strip_no_indent_marker(line: str) -> tuple[str, bool]:
    """解析 <!-- no-indent --> 标记。"""
    s = line.strip()
    if s.startswith(NO_INDENT):
        return s[len(NO_INDENT) :].lstrip(), True
    return line, False


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
