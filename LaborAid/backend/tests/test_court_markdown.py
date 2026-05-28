"""法院文书 Markdown / 预览 HTML 测试。"""

from app.services.docgen.court_document_styles import COURT_DOCUMENT_CSS
from app.services.docgen.court_markdown import build_preview_html


def test_build_preview_html_wraps_court_document():
    html = build_preview_html("## 申请人\n\n姓名：张三", title="劳动仲裁申请书")
    assert html.startswith('<div class="court-document">')
    assert "</div>" in html
    assert "<h2>申请人</h2>" in html

    with_title = build_preview_html("申请人：张三", title="劳动仲裁申请书")
    assert "<h1" in with_title


def test_strip_inline_color_on_raw_heading():
    html = build_preview_html('<h2 style="color:blue">申请人</h2>\n\n<p>正文</p>', title=None)
    assert "color:blue" not in html
    assert "申请人" in html


def test_court_css_uses_black_for_headings():
    assert "color: #000" in COURT_DOCUMENT_CSS
    assert ".court-document h2" in COURT_DOCUMENT_CSS
    assert "SimHei" in COURT_DOCUMENT_CSS
