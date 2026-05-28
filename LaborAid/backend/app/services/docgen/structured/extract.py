"""从案情描述中抽取结构化字段（LLM 输出 JSON，再由 renderers 拼版）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.docgen.structured.helpers import (
    fallback_parse_json,
    merge_payload,
    seed_from_parsed_case,
)
from app.services.docgen.structured.schemas import STRUCTURED_FIELD_SCHEMAS
from app.services.docgen.template_structure import build_extraction_schema, merge_template_into_extraction_prompt_block

logger = logging.getLogger(__name__)

STRUCTURED_EXTRACTION_SYSTEM = """你是法律文书信息抽取助手。根据案情与结构化案件信息，填充 JSON 各字段。
规则：
1. 仅输出一个合法 JSON 对象，不要 markdown 代码块，不要解释。
2. 信息缺失用空字符串 ""，不要编造与案情矛盾的姓名、金额、日期。
3. 请求/诉求类字段用完整句子，多项可换行分隔。
4. 日期格式：XXXX年XX月XX日。
5. 不要输出问候语、助手自我介绍。"""


def _schema_prompt_block(doc_type: str, template: Any = None) -> str:
    fields = build_extraction_schema(doc_type, template)
    if not fields:
        fields = STRUCTURED_FIELD_SCHEMAS.get(doc_type, {})
    lines = ["{"]
    for key, desc in fields.items():
        lines.append(f'  "{key}": "",  // {desc}')
    lines.append("}")
    return "\n".join(lines)


def build_extraction_user_prompt(
    doc_type_name: str,
    doc_type: str,
    case_facts: str,
    parsed_case: dict[str, Any],
    related_laws: str,
    extra_instructions: str | None,
    template: Any = None,
    research_context: str | None = None,
    preseed: dict[str, Any] | None = None,
) -> str:
    schema = _schema_prompt_block(doc_type, template)
    tpl_hint = merge_template_into_extraction_prompt_block(template) if template else ""
    preseed_block = ""
    if preseed:
        preseed_block = (
            "\n## 已确认信息（优先沿用，勿改姓名/单位名称）\n"
            + json.dumps(preseed, ensure_ascii=False, indent=2)
            + "\n"
        )
    research_block = ""
    if research_context and research_context.strip():
        research_block = f"\n## 研究报告摘要\n{research_context.strip()[:4000]}\n"
    return f"""请为《{doc_type_name}》抽取字段，输出 JSON（键名必须与下列一致）：

{schema}
{preseed_block}
{tpl_hint}
{research_block}

## 案情描述
{case_facts}

## 已解析案件信息
{json.dumps(parsed_case, ensure_ascii=False, indent=2)}

## 相关法规（供法律依据等字段参考）
{(related_laws or "无")[:8000]}

## 额外指示
{extra_instructions or "无"}

仅输出 JSON。"""


async def extract_structured_payload(
    engine: Any,
    doc_type: str,
    doc_type_name: str,
    case_facts: str,
    parsed_case: dict[str, Any],
    related_laws: str = "",
    extra_instructions: str | None = None,
    template: Any = None,
    research_context: str | None = None,
    preseed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seed = {**seed_from_parsed_case(parsed_case), **(preseed or {})}
    user_prompt = build_extraction_user_prompt(
        doc_type_name,
        doc_type,
        case_facts,
        parsed_case,
        related_laws,
        extra_instructions,
        template=template,
        research_context=research_context,
        preseed=preseed,
    )
    raw = await engine._call_claude(
        system=STRUCTURED_EXTRACTION_SYSTEM,
        user=user_prompt,
        max_tokens=4096,
    )
    extracted: dict[str, Any] = {}
    if raw and raw.strip():
        try:
            extracted = engine._parse_json_response(raw)
        except Exception as e:
            logger.warning("Structured extraction JSON parse failed: %s", e)
            extracted = fallback_parse_json(raw)
    return merge_payload(seed, extracted)
