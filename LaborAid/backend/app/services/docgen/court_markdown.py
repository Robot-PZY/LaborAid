"""法院文书 Markdown 解析 — 供 HTML 预览、HTML 导出与 Word 导出共用同一套规则。"""

import re
from html import escape

from app.services.docgen.structured.helpers import NO_INDENT, strip_no_indent_marker

_INLINE_COLOR_STYLE_RE = re.compile(
    r'\s*style\s*=\s*["\'][^"\']*(?:color|background)[^"\']*["\']',
    re.IGNORECASE,
)
_RAW_HEADING_RE = re.compile(r"^<h([1-6])\b[^>]*>.*</h\1>\s*$", re.IGNORECASE | re.DOTALL)

# 右对齐段落模式：签名、日期、此致后的法院名等
_RIGHT_ALIGN_PATTERNS = re.compile(
    r"^(?:起诉人|申请人|答辩人|上诉人|被上诉人|反诉原告|反诉被告|"
    r"代理人|辩护人|投诉人|质证人|异议人|出具人|调解员|"
    r"律师|仲裁员|书记员|"
    r"XXXX年|××××年|\d{4}年|"
    r"日期[：:])",
)

# 落款区块起始标记
_CLOSING_MARKERS = {"## 落款", "## 落款："}


def _strip_inline_color_styles(html: str) -> str:
    """移除 LLM 可能注入的 color/background 行内样式，避免预览标题发蓝。"""
    return _INLINE_COLOR_STYLE_RE.sub("", html)


def format_inline_html(text: str) -> str:
    """行内格式：**粗体**、__粗体__、*斜体* → HTML。"""
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # 模板变量缺失提示高亮：【xxx待补充】 → 红色高亮
    text = re.sub(
        r"【([^】]*待补充[^】]*)】",
        r'<span class="template-hint">【\1】</span>',
        text,
    )
    return text


def _is_right_align_candidate(text: str) -> bool:
    """判断文本是否应右对齐（签名行、日期行等）。"""
    return bool(_RIGHT_ALIGN_PATTERNS.match(text))


def markdown_to_html_body(text: str) -> str:
    """将 Markdown 正文转为 HTML 片段（不含外层文档与文书标题）。"""
    lines = text.split("\n")
    html_parts: list[str] = []
    in_list = False
    list_type: str | None = None
    in_closing = False

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            html_parts.append('<p class="no-indent">&nbsp;</p>')
            i += 1
            continue

        stripped, no_indent = strip_no_indent_marker(stripped)

        # 检测落款区块 → 后续 no-indent 行均右对齐
        if stripped in _CLOSING_MARKERS:
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            in_closing = True
            i += 1
            continue

        if no_indent and stripped:
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            # 落款区块内的 no-indent 行或匹配签名模式的行 → 右对齐
            if in_closing or _is_right_align_candidate(stripped):
                html_parts.append(f'<p class="right-align">{format_inline_html(stripped)}</p>')
            else:
                html_parts.append(f'<p class="no-indent">{format_inline_html(stripped)}</p>')
            i += 1
            continue

        if _RAW_HEADING_RE.match(stripped):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            in_closing = False
            html_parts.append(_strip_inline_color_styles(stripped))
            i += 1
            continue

        if stripped.startswith("#### "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            html_parts.append(f'<h4>{format_inline_html(stripped[5:])}</h4>')
            i += 1
            continue

        if stripped.startswith("### "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            in_closing = False
            html_parts.append(f"<h3>{format_inline_html(stripped[4:])}</h3>")
            i += 1
            continue

        if stripped.startswith("## "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            in_closing = False
            html_parts.append(f"<h2>{format_inline_html(stripped[3:])}</h2>")
            i += 1
            continue

        if stripped.startswith("# "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            in_closing = False
            html_parts.append(f'<h1 class="center">{format_inline_html(stripped[2:])}</h1>')
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            table_html, rows_consumed = _parse_table(lines, i)
            html_parts.append(table_html)
            i += rows_consumed
            continue

        ordered_match = re.match(r"^(\d+)[.、)]\s(.*)", stripped)
        if ordered_match:
            if in_list and list_type != "ol":
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            if not in_list:
                html_parts.append('<ol class="legal-list">')
                in_list = True
                list_type = "ol"
            html_parts.append(f"<li>{format_inline_html(ordered_match.group(2))}</li>")
            i += 1
            continue

        if re.match(r"^[-*]\s", stripped):
            if in_list and list_type != "ul":
                html_parts.append(f"</{list_type}>")
                in_list = False
                list_type = None
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
                list_type = "ul"
            html_parts.append(f"<li>{format_inline_html(stripped[2:])}</li>")
            i += 1
            continue

        if in_list:
            html_parts.append(f"</{list_type}>")
            in_list = False
            list_type = None

        # 此致 特殊处理 — 加间距
        if stripped in ("此致", "此致：", "此致:"):
            html_parts.append(f'<p class="no-indent" style="margin-top:12pt">{format_inline_html(stripped)}</p>')
            i += 1
            continue

        html_parts.append(f"<p>{format_inline_html(stripped)}</p>")
        i += 1

    if in_list and list_type:
        html_parts.append(f"</{list_type}>")

    return "\n".join(html_parts)


def build_preview_html(content: str, title: str | None = None) -> str:
    """生成完整预览 HTML（含标题逻辑，与 html_export / Word 一致）。"""
    content = content or ""
    parts: list[str] = []
    if title and not content.lstrip().startswith("#"):
        parts.append(f'<h1 class="center">{escape(title)}</h1>')
    parts.append(markdown_to_html_body(content))
    body = _strip_inline_color_styles("\n".join(parts))
    return f'<div class="court-document">{body}</div>'


def _parse_table(lines: list[str], start_idx: int) -> tuple[str, int]:
    table_lines: list[list[str]] = []
    j = start_idx
    while j < len(lines) and lines[j].strip().startswith("|") and "|" in lines[j].strip()[1:]:
        stripped_line = lines[j].strip()
        if re.match(r"^\|[\s\-:|]+\|$", stripped_line):
            j += 1
            continue
        cells = [c.strip() for c in stripped_line.split("|")[1:-1]]
        table_lines.append(cells)
        j += 1

    if not table_lines:
        return ("<p></p>", 1)

    max_cols = max(len(row) for row in table_lines)
    html_parts = ["<table>"]
    for row_idx, row in enumerate(table_lines):
        tag = "th" if row_idx == 0 else "td"
        cells_html = ""
        for col_idx in range(max_cols):
            cell_text = row[col_idx] if col_idx < len(row) else ""
            cells_html += f"<{tag}>{format_inline_html(cell_text)}</{tag}>"
        html_parts.append(f"<tr>{cells_html}</tr>")
    html_parts.append("</table>")
    return ("\n".join(html_parts), j - start_idx)
