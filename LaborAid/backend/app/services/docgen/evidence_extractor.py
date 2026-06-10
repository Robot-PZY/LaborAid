"""证据事实提取引擎。

从证据材料中提取关键事实信息，而非原样复制证据原文。
用于填充文书模板中的变量。
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 证据提取系统提示词
EVIDENCE_EXTRACTION_SYSTEM = """你是法律事实提取助手。
根据用户提供的证据材料，提取关键事实信息，输出 JSON。

规则：
1. 仅输出一个合法 JSON 对象，不要 markdown 代码块，不要解释。
2. 信息缺失用空字符串 ""，不要编造与证据矛盾的姓名、金额、日期。
3. 从证据中提取客观事实，不要添加主观判断。
4. 日期格式：XXXX年XX月XX日。
5. 金额精确到元，同时提供阿拉伯数字和中文大写。
6. 时间线按时间顺序排列，每个节点包含：时间、事件、涉及金额（如有）。
7. 证据清单每项包含：证据名称、证明目的、证据形式（书证/电子数据/证人证言等）。
8. 不要输出问候语、助手自我介绍。"""

# 证据提取用户提示词模板
EVIDENCE_EXTRACTION_USER_TEMPLATE = """请从以下证据材料中提取关键事实信息：

## 证据材料
{evidence_text}

## 需要提取的信息

请输出以下 JSON 结构：
{{
  "hire_date": "入职时间（XXXX年XX月XX日）",
  "resignation_date": "离职时间（如有，XXXX年XX月XX日）",
  "monthly_salary": "月工资金额（阿拉伯数字，如8000）",
  "monthly_salary_cn": "月工资中文大写（如捌仟元整）",
  "arrears_amount": "拖欠工资金额（阿拉伯数字）",
  "arrears_amount_cn": "拖欠工资金额中文大写",
  "arrears_period_start": "欠薪起始时间（XXXX年XX月）",
  "arrears_period_end": "欠薪结束时间（XXXX年XX月）",
  "timeline": [
    {{
      "date": "时间（XXXX年XX月XX日）",
      "event": "事件描述（简洁，50字以内）",
      "amount": "涉及金额（如有，阿拉伯数字）"
    }}
  ],
  "evidence_list": [
    {{
      "name": "证据名称（如：劳动合同）",
      "purpose": "证明目的（如：证明劳动关系成立）",
      "type": "证据形式（书证/电子数据/证人证言/鉴定意见等）"
    }}
  ],
  "key_facts": "关键事实摘要（100-200字，概括核心争议）"
}}

注意：
- 如果证据中无法提取某个字段，留空字符串 ""
- timeline 按时间顺序排列，3-5个关键节点
- evidence_list 列出所有提到的证据
- key_facts 用法律语言概括，不要原样复制证据原文"""


async def extract_facts_from_evidence(
    engine: Any,
    evidence_text: str,
) -> dict[str, Any]:
    """从证据材料中提取关键事实。

    Args:
        engine: LLM 引擎
        evidence_text: 证据材料文本

    Returns:
        提取的事实字典
    """
    if not evidence_text or not evidence_text.strip():
        return {}

    user_prompt = EVIDENCE_EXTRACTION_USER_TEMPLATE.format(
        evidence_text=evidence_text[:8000]  # 限制长度
    )

    try:
        raw = await engine._call_claude(
            system=EVIDENCE_EXTRACTION_SYSTEM,
            user=user_prompt,
            max_tokens=2048,
        )

        if not raw or not raw.strip():
            logger.warning("Evidence extraction returned empty result")
            return {}

        # 尝试解析 JSON
        try:
            result = engine._parse_json_response(raw)
        except Exception:
            # 回退：尝试从文本中提取 JSON
            from app.services.docgen.structured.helpers import fallback_parse_json
            result = fallback_parse_json(raw)

        if not isinstance(result, dict):
            logger.warning("Evidence extraction returned non-dict result")
            return {}

        return result

    except Exception as e:
        logger.error("Evidence extraction failed: %s", e)
        return {}


def merge_evidence_facts(
    existing_payload: dict[str, Any],
    evidence_facts: dict[str, Any],
) -> dict[str, Any]:
    """将证据提取的事实合并到现有 payload 中。

    证据提取的字段优先级低于用户明确提供的字段，
    但高于 LLM 从案情描述中提取的字段。
    """
    if not evidence_facts:
        return existing_payload

    merged = dict(existing_payload)

    # 定义证据字段映射（证据字段 → payload 字段）
    field_mapping = {
        "hire_date": "hire_date",
        "resignation_date": "resignation_date",
        "monthly_salary": "monthly_salary",
        "monthly_salary_cn": "monthly_salary_cn",
        "arrears_amount": "arrears_amount",
        "arrears_amount_cn": "arrears_amount_cn",
        "arrears_period_start": "dispute_start",
        "arrears_period_end": "dispute_end",
        "key_facts": "dispute_details",
    }

    for evidence_key, payload_key in field_mapping.items():
        value = evidence_facts.get(evidence_key, "")
        if value and value != "":
            # 只在 payload 中该字段为空时才填充
            if not merged.get(payload_key):
                merged[payload_key] = value

    # 处理时间线（转换为文本）
    timeline = evidence_facts.get("timeline", [])
    if timeline and not merged.get("dispute_details"):
        timeline_text = "\n".join(
            f"- {item.get('date', '')}：{item.get('event', '')}"
            for item in timeline
            if item.get("date") or item.get("event")
        )
        if timeline_text:
            merged["dispute_details"] = timeline_text

    # 处理证据清单（转换为 Markdown 表格文本）
    evidence_list = evidence_facts.get("evidence_list", [])
    if evidence_list and not merged.get("evidence"):
        evidence_lines = []
        for i, item in enumerate(evidence_list, 1):
            name = item.get("name", "")
            purpose = item.get("purpose", "")
            if name:
                evidence_lines.append(f"{i}. {name}—{purpose}")
        if evidence_lines:
            merged["evidence"] = "\n".join(evidence_lines)

    return merged
