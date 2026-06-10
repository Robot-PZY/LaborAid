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

STRUCTURED_EXTRACTION_SYSTEM = """你是法律文书变量提取助手。请根据用户提供的案情描述和已解析案件信息，提取模板所需的变量值，输出 JSON。

规则：
1. 仅输出一个合法 JSON 对象，不要 markdown 代码块，不要解释。
2. 信息缺失用空字符串 ""，不要编造与案情矛盾的姓名、金额、日期。
3. 请求/诉求类字段用完整句子，每项须包含：请求事项 + 具体金额（精确到元）+ 计算方式或法律依据。金额须同时使用中文大写和阿拉伯数字。
4. 日期格式：XXXX年XX月XX日。
5. dispute_details 字段须按时间顺序详细叙述争议经过，包含时间、地点、人物、经过、结果，不少于200字。不得原样复制用户输入的原始证据数据（如银行流水、微信聊天记录原文），须提取关键信息后改写为法律语言。
6. legal_analysis_expansion 字段须采用三段论：法条→事实→结论，不少于150字。
7. 不要输出问候语、助手自我介绍。
8. 【重要】请充分利用用户输入中的所有信息。用户在案情描述、关联案件中已经填写的内容（如公司名称、工作地区、行业工种、欠款金额、入职时间等）必须提取到对应字段中，不要留空。
9. 【重要】如果用户在案情描述中提到了具体数字（金额、日期、人数等），必须提取到对应字段。
10. 【重要】对于 dispute_details 和 legal_analysis_expansion，即使用户输入较短，你也应当基于已有信息进行合理扩展和补充，生成符合法律文书规范的完整内容。"""


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

    # 注入模板上下文：告诉 LLM 文书的事实与理由部分将用预定义模板渲染
    template_context_block = ""
    try:
        from app.services.docgen.templates.legal_templates import (
            get_facts_template, get_variable_descriptions,
        )
        facts_tpl = get_facts_template(doc_type)
        var_descs = get_variable_descriptions(doc_type)
        if facts_tpl and var_descs:
            var_desc_lines = "\n".join(
                f'  "{k}": "{v}"' for k, v in var_descs.items()
            )
            template_context_block = f"""
## 模板上下文（重要）
本文书的「事实与理由」部分将使用预定义法律文本模板渲染，你只需提取以下变量值填入模板：

需要提取的模板变量：
{{
{var_desc_lines}
}}

模板结构预览：
{facts_tpl[:1500]}...

⚠️ 注意：
- 你只需要输出上述变量的 JSON 值，不需要输出完整文书
- dispute_details 须按时间线改写为正式法律语言，不得原样复制用户输入的原始数据（如银行流水、微信记录）
- 【关键】请仔细分析案情描述和已解析案件信息，提取所有可用的具体信息（金额、日期、公司名称、工作地点等）
- 【关键】如果某个变量在案情中有提及但未明确数值，请基于上下文合理推断并填写
- 只有完全无法推断的变量才留空字符串 ""
"""
    except ImportError:
        pass

    return f"""请为《{doc_type_name}》抽取字段，输出 JSON（键名必须与下列一致）：

{schema}
{template_context_block}
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
