"""结构化 enrich / 校验测试。"""

from app.services.docgen.structured.enrich import (
    enrich_structured_payload,
    extract_shared_bundle_fields,
    list_missing_required,
    list_weak_long_fields,
)
from app.services.docgen.structured.pipeline import merge_bundle_preseed


def test_enrich_facts_from_summary():
    payload = enrich_structured_payload(
        "application",
        {"applicant_name": "张三"},
        case_facts="向北京朝阳区劳动人事争议仲裁委员会申请仲裁",
        parsed_case={"facts_summary": "2020年入职，2024年欠薪五万元。"},
        legal_basis_section="## 法律依据参考\n《劳动合同法》第三十八条",
    )
    assert "2020年入职" in payload["facts"]
    assert "劳动合同法" in payload["legal_basis"]
    assert "劳动人事争议仲裁委员会" in payload["arbitration_commission"]


def test_missing_required():
    missing = list_missing_required("application", {"applicant_name": "张三"})
    assert "respondent_name" in missing
    assert "requests" in missing


def test_weak_long_fields():
    weak = list_weak_long_fields("application", {"facts": "太短"})
    assert "facts" in weak


def test_bundle_shared_merge():
    a = {"applicant_name": "张三", "requests": "支付工资"}
    b = merge_bundle_preseed({}, a)
    c = merge_bundle_preseed(b, {"defendant_name": "甲公司", "applicant_name": "李四"})
    assert c["applicant_name"] == "李四"
    assert c["defendant_name"] == "甲公司"
    assert extract_shared_bundle_fields(a)["requests"] == "支付工资"
