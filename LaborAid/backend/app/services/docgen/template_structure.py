"""模板 structure 解析（无 structured 包依赖，供 extract/seed 使用）。"""

from __future__ import annotations

import json
from typing import Any

from app.services.docgen.structured.schemas import STRUCTURED_FIELD_SCHEMAS


def structure_to_variables(sections: list[dict]) -> list[dict]:
    out: list[dict] = []
    for sec in sections:
        for field in sec.get("fields") or []:
            if not isinstance(field, dict) or not field.get("key"):
                continue
            out.append({
                "name": field["key"],
                "label": field.get("label", field["key"]),
                "type": field.get("type", "text"),
                "required": bool(field.get("required", False)),
                "section": sec.get("name", ""),
            })
    return out


def sections_preview_from_structure(structure: dict | None) -> list[str]:
    if not structure or not isinstance(structure, dict):
        return []
    names: list[str] = []
    for sec in structure.get("sections") or []:
        if isinstance(sec, dict) and sec.get("name"):
            names.append(str(sec["name"]))
    return names


def field_keys_from_structure(structure: dict | None) -> list[str]:
    keys: list[str] = []
    if not structure or not isinstance(structure, dict):
        return keys
    for sec in structure.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        for field in sec.get("fields") or []:
            if isinstance(field, dict) and field.get("key"):
                keys.append(str(field["key"]))
    return keys


def _parse_structure(template: Any) -> dict:
    structure = getattr(template, "structure", None) or {}
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except json.JSONDecodeError:
            structure = {}
    return structure if isinstance(structure, dict) else {}


def build_extraction_schema(doc_type: str, template: Any = None) -> dict[str, str]:
    base = dict(STRUCTURED_FIELD_SCHEMAS.get(doc_type, {}))
    if not template:
        return base
    structure = _parse_structure(template)
    for sec in structure.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        for field in sec.get("fields") or []:
            if not isinstance(field, dict):
                continue
            key = field.get("key")
            if key:
                key = str(key).strip()
                label = field.get("label") or key
                base[key] = f"{label}（{sec.get('name', '')}）" if sec.get("name") else str(label)
    return base


def merge_template_into_extraction_prompt_block(template: Any) -> str:
    structure = _parse_structure(template)
    if not structure:
        return ""
    lines = ["## 本模板章节与字段（须全部填写 JSON 键）"]
    for sec in structure.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        name = sec.get("name", "未命名")
        fields = sec.get("fields") or []
        keys = [f.get("key") for f in fields if isinstance(f, dict) and f.get("key")]
        if keys:
            lines.append(f"- **{name}**：{', '.join(keys)}")
        else:
            lines.append(f"- **{name}**")
    if getattr(template, "description", None):
        lines.append(f"\n模板说明：{template.description}")
    return "\n".join(lines)
