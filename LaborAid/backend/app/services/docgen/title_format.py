"""文书标题格式化。"""

from __future__ import annotations


def format_case_document_title(
    *,
    case_title: str | None,
    doc_type_label: str,
    plaintiff: str = "",
    defendant: str = "",
) -> str:
    """生成「案件名-文书名」或当事人诉称式标题。"""
    label = (doc_type_label or "法律文书").strip()
    case = (case_title or "").strip()
    if case:
        if case.endswith(label) or f"-{label}" in case or f"—{label}" in case:
            return case
        return f"{case}-{label}"
    if plaintiff and defendant:
        return f"{plaintiff}诉{defendant}{label}"
    return label
