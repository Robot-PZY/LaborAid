"""结构化文书生成管线：抽取 →  enrich → 定向补全 → 渲染。"""

from __future__ import annotations

import logging
from typing import Any

from app.services.docgen.content_sanitize import sanitize_legal_document_content
from app.services.docgen.legal_citation_normalize import normalize_markdown_citations
from app.services.docgen.content_quality_check import run_quality_checks
from app.services.docgen.structured.enrich import (
    enrich_structured_payload,
    extract_shared_bundle_fields,
    is_empty_value,
    list_missing_required,
    list_weak_long_fields,
)
from app.services.docgen.structured.extract import extract_structured_payload
from app.services.docgen.structured.refine import refine_structured_fields
from app.services.docgen.structured.renderers import render_structured_document

logger = logging.getLogger(__name__)

# 每份文书最多补全轮次（避免过多 LLM 调用）
MAX_REFINE_ROUNDS = 1


async def run_structured_generation(
    engine: Any,
    *,
    doc_type: str,
    doc_type_name: str,
    case_facts: str,
    parsed_case: dict[str, Any],
    combined_laws: str,
    legal_basis_section: str = "",
    extra_instructions: str | None = None,
    template: Any = None,
    research_context: str | None = None,
    bundle_preseed: dict[str, Any] | None = None,
    evidence_text: str = "",
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """
    返回 (markdown_content, payload, debug_info)
    """
    # 阶段1: 从证据中提取关键事实（如果有证据材料）
    evidence_facts = {}
    if evidence_text and evidence_text.strip():
        try:
            from app.services.docgen.evidence_extractor import extract_facts_from_evidence
            evidence_facts = await extract_facts_from_evidence(engine, evidence_text)
            logger.info("Extracted %d facts from evidence", len(evidence_facts))
        except Exception as e:
            logger.warning("Evidence extraction failed: %s", e)

    payload = await extract_structured_payload(
        engine,
        doc_type,
        doc_type_name,
        case_facts,
        parsed_case,
        related_laws=combined_laws,
        extra_instructions=extra_instructions,
        template=template,
        research_context=research_context,
        preseed=bundle_preseed,
    )

    # 阶段2: 合并证据提取的事实（优先级：用户输入 > 证据提取 > LLM案情提取）
    if evidence_facts:
        from app.services.docgen.evidence_extractor import merge_evidence_facts
        payload = merge_evidence_facts(payload, evidence_facts)

    payload = enrich_structured_payload(
        doc_type,
        payload,
        case_facts=case_facts,
        parsed_case=parsed_case,
        legal_basis_section=legal_basis_section,
        research_context=research_context,
    )

    debug: dict[str, Any] = {
        "missing_after_enrich": list_missing_required(doc_type, payload),
        "template_id": getattr(template, "id", None) if template else None,
        "template_name": getattr(template, "name", None) if template else None,
    }

    # 模板变量填充率统计
    try:
        from app.services.docgen.templates.legal_templates import get_template_variables
        tpl_vars = get_template_variables(doc_type)
        if tpl_vars:
            filled_vars = [v for v in tpl_vars if not is_empty_value(payload.get(v))]
            debug["template_fill_rate"] = len(filled_vars) / len(tpl_vars)
            debug["template_filled"] = filled_vars
            debug["template_missing"] = [v for v in tpl_vars if v not in filled_vars]
    except ImportError:
        pass

    weak = list_weak_long_fields(doc_type, payload)
    missing = list_missing_required(doc_type, payload)
    to_refine = list(dict.fromkeys(weak + missing))  # 去重保序

    if to_refine and MAX_REFINE_ROUNDS > 0:
        try:
            payload = await refine_structured_fields(
                engine,
                doc_type,
                doc_type_name,
                payload,
                to_refine[:6],
                case_facts,
                parsed_case,
                related_laws=combined_laws,
            )
            payload = enrich_structured_payload(
                doc_type,
                payload,
                case_facts=case_facts,
                parsed_case=parsed_case,
                legal_basis_section=legal_basis_section,
            )
            debug["refined_fields"] = to_refine[:6]
        except Exception as e:
            logger.warning("Structured refine failed for %s: %s", doc_type, e)

    content = render_structured_document(doc_type, payload)
    content = sanitize_legal_document_content(content, doc_type_name)

    # 法条引用规范化
    content = normalize_markdown_citations(content)

    # 内容质量检查（仅记录日志，不阻断流程）
    quality = run_quality_checks(content, doc_type, payload=payload)
    if not quality["passed"]:
        logger.warning(
            "Quality check warnings for %s: %s",
            doc_type,
            "; ".join(quality["warnings"]),
        )
    debug["quality"] = quality

    debug["missing_final"] = list_missing_required(doc_type, payload)
    return content, payload, debug


def merge_bundle_preseed(existing: dict[str, Any], new_payload: dict[str, Any]) -> dict[str, Any]:
    return {**existing, **extract_shared_bundle_fields(new_payload)}
