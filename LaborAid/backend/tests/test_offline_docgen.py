"""离线文书兜底 — 不依赖 LLM 与数据库。"""

from app.services.docgen.offline_fallback import (
    build_offline_structured_document,
    rule_parse_case,
)


def test_rule_parse_case_extracts_parties():
    text = "原告李强，被告华城建设劳务有限公司，拖欠工资24000元。"
    parsed = rule_parse_case(text)
    assert parsed["parties"]["plaintiff"]["name"] == "李强"
    assert "华城" in parsed["parties"]["defendant"]["name"]


def test_offline_structured_application_renders():
    result = build_offline_structured_document(
        doc_type="application",
        case_facts="原告李强，被告华城建设劳务有限公司，拖欠工资24000元。",
    )
    assert "劳动仲裁申请书" in result["content"]
    assert result["metadata"]["generation_mode"] == "offline_fallback"
    assert len(result["content"]) > 200
