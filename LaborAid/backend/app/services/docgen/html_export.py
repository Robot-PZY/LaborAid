"""HTML导出 — 严格仿宋字体法院标准排版（与 Word 导出、前端预览共用解析规则）。"""

import asyncio
import re
from html import escape
from pathlib import Path

from app.services.docgen.court_document_styles import COURT_DOCUMENT_CSS
from app.services.docgen.court_markdown import build_preview_html


async def export_to_html(doc, output_dir: Path) -> str:
    """将文书内容导出为法院标准排版的HTML文件。"""
    title = doc.title or "法律文书"
    content = doc.content or ""
    html_body = build_preview_html(content, title=title)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
  @page {{
    size: A4;
    margin: 3.7cm 2.6cm 3.5cm 2.8cm;
    @bottom-center {{
      content: "— " counter(page) " —";
      font-family: "Times New Roman", serif;
      font-size: 10pt;
    }}
  }}
  body {{
    font-family: "FangSong_GB2312", "仿宋_GB2312", "FangSong", "仿宋", "STFangsong", serif;
    font-size: 16pt;
    line-height: 28.8pt;
    color: #000;
    max-width: 210mm;
    margin: 0 auto;
    padding: 3.7cm 2.6cm 3.5cm 2.8cm;
  }}
{COURT_DOCUMENT_CSS.replace(".court-document", "body")}
  @media print {{
    body {{
      padding: 0;
    }}
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    filename = f"{doc.id}_{_safe_filename(title)}.html"
    filepath = output_dir / filename
    await asyncio.to_thread(filepath.write_text, html, "utf-8")
    return str(filepath)


def _safe_filename(title: str) -> str:
    return re.sub(r"[^\w一-鿿]", "_", title)[:50]
