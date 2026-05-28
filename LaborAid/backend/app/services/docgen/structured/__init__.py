"""lawgpt 风格：JSON 抽取 + 多模板固定 Markdown 渲染。"""

from __future__ import annotations

from typing import Any

from app.services.docgen.structured.renderers import RENDERERS, render_structured_document
from app.services.docgen.structured.schemas import STRUCTURED_FIELD_SCHEMAS

STRUCTURED_DOC_TYPES = frozenset(RENDERERS.keys())


def has_structured_renderer(doc_type: str) -> bool:
    return doc_type in STRUCTURED_DOC_TYPES


def __getattr__(name: str) -> Any:
    if name == "extract_structured_payload":
        from app.services.docgen.structured.extract import extract_structured_payload

        return extract_structured_payload
    if name == "run_structured_generation":
        from app.services.docgen.structured.pipeline import run_structured_generation

        return run_structured_generation
    if name == "merge_bundle_preseed":
        from app.services.docgen.structured.pipeline import merge_bundle_preseed

        return merge_bundle_preseed
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "STRUCTURED_DOC_TYPES",
    "STRUCTURED_FIELD_SCHEMAS",
    "has_structured_renderer",
    "render_structured_document",
    "extract_structured_payload",
    "run_structured_generation",
    "merge_bundle_preseed",
]
