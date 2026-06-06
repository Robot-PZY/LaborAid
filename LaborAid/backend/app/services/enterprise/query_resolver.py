"""企业查询关键词解析 — 将用户简称/品牌名补全为工商登记名后再调企查查。"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# 统一社会信用代码（18 位）
_CREDIT_CODE_RE = re.compile(r"^[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}$", re.I)

# 已像完整工商登记名称的后缀
_FULL_NAME_MARKERS = (
    "有限责任公司",
    "股份有限公司",
    "有限公司",
    "合伙企业",
    "普通合伙",
    "有限合伙",
    "个体工商户",
    "工作室",
    "事务所",
    "合作社",
    "农民专业合作社",
)

_SYSTEM = """你是中国企业工商登记名称解析助手。劳动者要查询用人单位的工商信息与风险记录。
用户输入可能是简称、品牌名、集团俗称或口头称呼，企查查 API 需要**精确的工商登记全称**或**统一社会信用代码**才能命中。

请根据用户输入推断最可能被精确匹配的**单一**中国大陆企业工商登记全称。

规则：
1. 只返回 JSON，不要其他文字
2. search_key 必须是单一企业全称，或原样保留的统一社会信用代码
3. 若输入已是完整登记名或 18 位信用代码，原样返回 search_key
4. 简称/品牌名补全为常见主体公司全称（总部或主要运营实体优先）
5. 不要编造统一社会信用代码
6. 不要返回多个名称；无法判断时原样返回用户输入

返回格式：
{"search_key": "企业全称或信用代码", "reason": "简要说明"}"""


def looks_like_credit_code(text: str) -> bool:
    return bool(_CREDIT_CODE_RE.match(text.strip()))


def looks_like_full_company_name(text: str) -> bool:
    """输入已含典型企业类型后缀，视为完整登记名，无需 LLM 补全。"""
    normalized = text.strip()
    if len(normalized) < 4:
        return False
    return any(marker in normalized for marker in _FULL_NAME_MARKERS)


def needs_llm_resolution(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    if looks_like_credit_code(normalized):
        return False
    return not looks_like_full_company_name(normalized)


def _parse_json_object(text: str) -> dict | None:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", t)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _sanitize_resolved_key(raw_input: str, candidate: str) -> str | None:
    resolved = (candidate or "").strip()
    if not resolved or len(resolved) > 100:
        return None
    if resolved == raw_input:
        return resolved
    if looks_like_credit_code(resolved):
        return resolved.upper()
    if looks_like_full_company_name(resolved):
        return resolved
    return None


async def _resolve_via_llm(raw_input: str, llm) -> str | None:
    prompt = f"""用户输入：{raw_input}

请输出 JSON。"""

    response = await llm.client.messages.create(
        model=llm.model,
        max_tokens=min(256, llm.max_tokens),
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = ""
    if response.content:
        text = (response.content[0].text or "").strip()

    data = _parse_json_object(text)
    if not data:
        return None

    return _sanitize_resolved_key(raw_input, str(data.get("search_key") or ""))


async def resolve_enterprise_search_key(raw_input: str, *, llm=None) -> str:
    """将用户输入解析为适合企查查精确查询的关键词；失败时回退原输入。"""
    key = raw_input.strip()
    if not key or not needs_llm_resolution(key):
        return key

    if not llm or not getattr(llm, "client", None):
        logger.debug("Enterprise resolver: no LLM, using raw input %r", key)
        return key

    try:
        resolved = await _resolve_via_llm(key, llm)
        if resolved:
            if resolved != key:
                logger.info("Enterprise search resolved %r -> %r", key, resolved)
            return resolved
    except Exception as exc:
        logger.warning("Enterprise search LLM resolve failed: %s", exc)

    return key
