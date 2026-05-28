from app.services.docgen.format_normalizer import normalize_freeform_markdown


def test_normalize_application_sections():
    raw = """劳动仲裁申请书

申请人：
姓名：张三

仲裁请求：
1. 支付工资

事实与理由：
欠薪事实

此致
仲裁委员会
"""
    out = normalize_freeform_markdown(raw, "application")
    assert "## 申请人" in out or "# 劳动仲裁申请书" in out
    assert "此致" in out
