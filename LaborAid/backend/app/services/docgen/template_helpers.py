"""模板 API 响应增强。"""

from __future__ import annotations

import json
from typing import Any

from app.services.docgen.template_meta import category_for_type, supports_structured_generation
from app.services.docgen.template_structure import (
    field_keys_from_structure,
    sections_preview_from_structure,
)


def enrich_template_dict(tmpl: Any) -> dict[str, Any]:
    structure = getattr(tmpl, "structure", None) or {}
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except json.JSONDecodeError:
            structure = {}
    fmt = getattr(tmpl, "format_rules", None) or {}
    if isinstance(fmt, str):
        try:
            fmt = json.loads(fmt)
        except json.JSONDecodeError:
            fmt = {}
    doc_type = getattr(tmpl, "type", "") or ""
    structured = supports_structured_generation(doc_type)
    return {
        "sections_preview": sections_preview_from_structure(structure),
        "field_count": len(field_keys_from_structure(structure)),
        "supports_structured": structured,
        "category": category_for_type(doc_type),
        "generation_mode": (fmt.get("generation_mode") if isinstance(fmt, dict) else None)
        or ("structured" if structured else "freeform"),
        "word_export_mode": (fmt.get("word_export") if isinstance(fmt, dict) else None) or "native",
    }
