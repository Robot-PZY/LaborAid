"""对结构化文书中薄弱字段做定向补全（小范围二次 LLM 调用）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.docgen.structured.enrich import field_labels_for_prompt, is_empty_value
from app.services.docgen.structured.helpers import merge_payload

logger = logging.getLogger(__name__)

REFINE_SYSTEM = """你是法律文书变量补全助手。
仅补全用户指定的 JSON 字段，输出完整 JSON 对象（包含所有请求的键）。

规则：
1. 不编造与案情矛盾的金额、姓名、日期。
2. 法条须与劳动争议相关。
3. 分项请求用完整句子，金额须同时使用中文大写和阿拉伯数字。
4. dispute_details 字段须按时间顺序详细叙述争议经过，不少于200字，不得原样复制用户输入的原始证据数据（如银行流水、微信聊天记录），须改写为法律语言。
5. legal_analysis_expansion 字段须采用三段论：法条→事实→结论，不少于150字。
6. 日期格式：XXXX年XX月XX日。
7. 仅输出 JSON，不要解释。"""


async def refine_structured_fields(
    engine: Any,
    doc_type: str,
    doc_type_name: str,
    payload: dict[str, Any],
    fields: list[str],
    case_facts: str,
    parsed_case: dict[str, Any],
    related_laws: str = "",
) -> dict[str, Any]:
    if not fields:
        return payload

    schema_block = field_labels_for_prompt(doc_type, fields)

    # 构建模板上下文提示（如果被补全的字段包含模板变量）
    template_hint = ""
    try:
        from app.services.docgen.templates.legal_templates import (
            get_facts_template, get_template_variables,
        )
        tpl_vars = get_template_variables(doc_type)
        tpl_fields_being_refined = [f for f in fields if f in tpl_vars]
        if tpl_fields_being_refined:
            tpl = get_facts_template(doc_type)
            if tpl:
                template_hint = f"""
## 模板上下文
以下字段是法律文本模板中的变量，请确保填写的值能正确嵌入模板：
- 待补全的模板变量：{', '.join(tpl_fields_being_refined)}

模板结构预览：
{tpl[:800]}
"""
    except ImportError:
        pass

    user = f"""文书类型：《{doc_type_name}》
请仅完善下列字段（根据案情写实、充分展开，事实按时间顺序，请求项明确金额）：

{schema_block}
{template_hint}
## 案情
{case_facts[:12000]}

## 已有信息（勿矛盾）
{json.dumps({k: payload.get(k) for k in payload if not is_empty_value(payload.get(k))}, ensure_ascii=False, indent=2)}

## 法规参考
{(related_laws or "无")[:6000]}

仅输出 JSON。"""

    raw = await engine._call_claude(system=REFINE_SYSTEM, user=user, max_tokens=3072)
    if not raw or not raw.strip():
        return payload
    try:
        patch = engine._parse_json_response(raw)
    except Exception:
        from app.services.docgen.structured.helpers import fallback_parse_json

        patch = fallback_parse_json(raw)
    if not isinstance(patch, dict):
        return payload
    # 只合并请求的字段
    filtered = {k: patch[k] for k in fields if k in patch and not is_empty_value(patch.get(k))}
    return merge_payload(payload, filtered)
