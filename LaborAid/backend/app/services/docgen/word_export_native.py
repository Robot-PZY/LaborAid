"""Word 导出（LegalDocGen 思路）— 使用 Word 内置标题样式，避免手搓字体导致版式怪异。

LegalDocGen 的 export_service 核心做法：
- doc.add_heading() 映射 Markdown # / ## / ###
- 正文 add_paragraph()，不强制方正小标宋/仿宋等（由 Word 主题渲染）
- 不用复杂 XML 水印、章节前分页

本模块供 LaborAid 默认导出使用；法院精细排版见 word_export.py（court 模式）。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.services.docgen.word_export import _SAFE_FILENAME_RE, _sanitize_xml_text

# 正文字体：Windows 常见，缺失时 Word 自动回退
_BODY_FONT = "仿宋"
_BODY_FONT_FALLBACK = "FangSong"
_BODY_SIZE = Pt(12)
_LINE_SPACING = Pt(22)
_FIRST_LINE_INDENT = Cm(0.74)


def _set_east_asia_font(run, name: str) -> None:
    run.font.name = name
    r = run._element
    r_pr = r.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), name)


def _style_set_east_asia(style, latin: str, east_asia: str) -> None:
    style.font.name = latin
    r_pr = style._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), east_asia)


def _configure_document_styles(doc: Document) -> None:
    """统一 Normal / Heading 样式，打开 Word 时版式稳定。"""
    normal = doc.styles["Normal"]
    _style_set_east_asia(normal, _BODY_FONT_FALLBACK, _BODY_FONT)
    normal.font.size = _BODY_SIZE
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = _LINE_SPACING
    pf.space_after = Pt(6)

    for level, size in ((1, 22), (2, 16), (3, 14), (4, 12)):
        style_name = f"Heading {level}"
        if style_name not in doc.styles:
            continue
        h = doc.styles[style_name]
        _style_set_east_asia(h, _BODY_FONT_FALLBACK, "黑体" if level <= 2 else _BODY_FONT)
        h.font.bold = True
        h.font.size = Pt(size)


def _setup_page_simple(doc: Document) -> None:
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)


def _parse_inline_to_paragraph(p, text: str, *, bold_labels: bool = True) -> None:
    """支持 **加粗**；**标签**：值 常见于法律文书。"""
    safe = _sanitize_xml_text(text)
    if not safe:
        return
    parts = safe.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        run = p.add_run(part)
        _set_east_asia_font(run, _BODY_FONT)
        run.font.size = _BODY_SIZE
        if i % 2 == 1:
            run.bold = True
        elif bold_labels and (part.rstrip().endswith("：") or part.rstrip().endswith(":")):
            run.bold = True


def _add_body_paragraph(doc: Document, text: str, *, indent: bool = True) -> None:
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = _FIRST_LINE_INDENT
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.paragraph_format.line_spacing = _LINE_SPACING
    p.paragraph_format.space_after = Pt(4)
    _parse_inline_to_paragraph(p, text)


def add_markdown_to_document(
    doc: Document,
    content: str,
    *,
    first_line_indent: bool = True,
) -> None:
    """将 Markdown 写入 Document（LegalDocGen 风格 + 加粗行内）。"""
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("#### "):
            doc.add_heading(stripped[5:].strip(), level=4)
            i += 1
            continue
        if stripped.startswith("### "):
            doc.add_heading(stripped[4:].strip(), level=3)
            i += 1
            continue
        if stripped.startswith("## "):
            doc.add_heading(stripped[3:].strip(), level=2)
            i += 1
            continue
        if stripped.startswith("# "):
            h = doc.add_heading(stripped[2:].strip(), level=1)
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            table_rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_line = lines[i].strip()
                if re.match(r"^\|[\s\-:|]+\|$", row_line):
                    i += 1
                    continue
                cells = [c.strip() for c in row_line.split("|")[1:-1]]
                table_rows.append(cells)
                i += 1
            if table_rows:
                cols = max(len(r) for r in table_rows)
                table = doc.add_table(rows=len(table_rows), cols=cols)
                table.style = "Table Grid"
                for ri, row in enumerate(table_rows):
                    for ci in range(cols):
                        cell_text = row[ci] if ci < len(row) else ""
                        table.cell(ri, ci).text = _sanitize_xml_text(cell_text)
            continue

        ordered = re.match(r"^(\d+)[.、)]\s*(.*)", stripped)
        if ordered:
            _add_body_paragraph(doc, f"{ordered.group(1)}. {ordered.group(2)}", indent=first_line_indent)
            i += 1
            continue

        if re.match(r"^[-*]\s", stripped):
            _add_body_paragraph(doc, "• " + stripped[2:], indent=first_line_indent)
            i += 1
            continue

        if stripped in ("此致", "此致：", "此致:"):
            p = doc.add_paragraph("此致")
            p.paragraph_format.space_before = Pt(12)
            i += 1
            continue

        _add_body_paragraph(doc, stripped, indent=first_line_indent)
        i += 1


def build_document_from_markdown(
    content: str,
    *,
    title: str | None = None,
    author: str = "劳权智助",
) -> Document:
    doc = Document()
    _setup_page_simple(doc)
    _configure_document_styles(doc)

    core = doc.core_properties
    core.title = _sanitize_xml_text(title or "法律文书")
    core.author = author
    core.created = datetime.now()
    core.modified = datetime.now()

    body = (content or "").strip()
    if not body:
        body = "（文档内容为空）"

    if not body.lstrip().startswith("#") and title:
        h = doc.add_heading(_sanitize_xml_text(title), level=1)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    add_markdown_to_document(doc, body, first_line_indent=True)

    footer = doc.add_paragraph("本文书由劳权智助辅助生成，提交前请核对事实与法律依据。")
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(128, 128, 128)

    return doc


def safe_docx_filename(doc_id: Any, title: str) -> str:
    safe_title = _SAFE_FILENAME_RE.sub("", title or "")
    if not safe_title:
        safe_title = f"document_{doc_id}"
    return f"{doc_id}_{safe_title}.docx"
