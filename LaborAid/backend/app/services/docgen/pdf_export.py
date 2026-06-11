"""PDF导出 — 基于HTML转PDF（法院标准排版）"""

import asyncio
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


async def export_to_pdf(doc, output_dir: Path) -> str:
    """将文书内容导出为PDF文件（通过HTML中转）。

    排版参数与Word/HTML导出一致：
    - 页边距：上37mm 下35mm 左28mm 右26mm
    - A4纸张
    """
    from app.services.docgen.html_export import export_to_html

    try:
        # 先生成HTML
        html_path = await export_to_html(doc, output_dir)
        html_content = await asyncio.to_thread(Path(html_path).read_text, "utf-8")
    except Exception as exc:
        logger.exception("PDF export: HTML generation failed for doc %s: %s", getattr(doc, "id", "?"), exc)
        raise RuntimeError(f"PDF 导出失败：HTML 生成错误 - {exc}") from exc

    title = doc.title or "法律文书"
    filename = f"{doc.id}_{_safe_filename(title)}.pdf"
    pdf_path = output_dir / filename

    # 尝试使用 weasyprint
    try:
        from weasyprint import HTML
        await asyncio.to_thread(lambda: HTML(string=html_content).write_pdf(str(pdf_path)))
        return str(pdf_path)
    except ImportError:
        logger.warning("weasyprint not installed, trying alternative")
    except Exception as e:
        logger.warning("weasyprint failed: %s", e)

    # 备选：使用 pdfkit (需要 wkhtmltopdf)
    try:
        import pdfkit
        await asyncio.to_thread(
            pdfkit.from_string,
            html_content,
            str(pdf_path),
            {
                'encoding': 'UTF-8',
                'page-size': 'A4',
                'margin-top': '37mm',
                'margin-right': '26mm',
                'margin-bottom': '35mm',
                'margin-left': '28mm',
                'footer-center': '— [page] —',
                'footer-font-size': '10',
                'footer-spacing': '5',
            },
        )
        return str(pdf_path)
    except ImportError:
        logger.warning("pdfkit not installed either")
    except Exception as e:
        logger.warning("pdfkit failed: %s", e)

    # 备选：使用 xhtml2pdf（纯 Python，Windows 无需额外系统库）
    try:
        from xhtml2pdf import pisa
        from html import escape
        from app.services.docgen.court_document_styles import COURT_DOCUMENT_CSS
        from app.services.docgen.court_markdown import build_preview_html

        # xhtml2pdf 对 @page/counter 与部分高级 CSS 支持较弱，改用兼容模板
        body_html = build_preview_html(doc.content or "", title=doc.title or "法律文书")
        simple_css = COURT_DOCUMENT_CSS.replace(".court-document", "body")
        # xhtml2pdf 的 CSS 解析器对复杂字体声明兼容较差，回退为通用字体
        simple_css = re.sub(r"font-family\s*:\s*[^;]+;", "font-family: SimSun, serif;", simple_css)
        xhtml2pdf_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{escape(title)}</title>
<style>
body {{
  margin: 0;
  padding: 24pt 28pt;
  background: #fff;
}}
{simple_css}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

        def _build_with_xhtml2pdf():
            with open(pdf_path, "wb") as fp:
                status = pisa.CreatePDF(xhtml2pdf_html, dest=fp, encoding="utf-8")
                return bool(status.err)

        has_error = await asyncio.to_thread(_build_with_xhtml2pdf)
        if not has_error and pdf_path.exists() and pdf_path.stat().st_size > 0:
            return str(pdf_path)
        logger.warning("xhtml2pdf conversion reported errors")
    except ImportError:
        logger.warning("xhtml2pdf not installed")
    except Exception as e:
        logger.warning("xhtml2pdf failed: %s", e)

    # 最终备选
    logger.error("No PDF converter available for doc %s", getattr(doc, "id", "?"))
    raise RuntimeError(
        "PDF导出失败：请安装可用转换器。推荐先执行 `pip install xhtml2pdf`，"
        "或安装 weasyprint 所需系统库（Windows 需 GTK）。"
    )


def _safe_filename(title: str) -> str:
    import re
    return re.sub(r'[^\w一-鿿]', '_', title)[:50]
