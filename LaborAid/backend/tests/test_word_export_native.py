"""Word native 导出 smoke test。"""

from pathlib import Path

from app.services.docgen.word_export_native import build_document_from_markdown


def test_build_document_from_markdown(tmp_path):
    md = """# 劳动仲裁申请书

## 申请人

**姓名**：张三
**身份证号**：110101199001011234

## 仲裁请求

1. 支付拖欠工资50000元
2. 支付经济补偿金10000元

## 事实与理由

2020年1月入职，2024年6月起欠薪。

## 落款

此致
北京市朝阳区劳动人事争议仲裁委员会

申请人：[签名]
2024年12月1日
"""
    doc = build_document_from_markdown(md, title="劳动仲裁申请书")
    out = tmp_path / "test_native.docx"
    doc.save(str(out))
    assert out.exists()
    assert out.stat().st_size > 3000
