"""结构化文书渲染单元测试（不调用 LLM）。"""

from app.services.docgen.structured import (
    STRUCTURED_DOC_TYPES,
    has_structured_renderer,
    render_structured_document,
)
from app.services.docgen.structured.helpers import seed_from_parsed_case


def test_all_platform_types_registered():
    expected = {
        "application",
        "labor_supervision",
        "wage_demand_letter",
        "forced_termination_notice",
        "arbitration_authorization",
        "evidence_list",
        "complaint",
        "answer",
        "appeal",
        "agency_opinion",
        "legal_opinion",
        "lawyer_letter",
        "preservation_application",
        "labor_contract",
        "contract",
        "mediation",
        "settlement_agreement",
    }
    assert expected == set(STRUCTURED_DOC_TYPES)


def test_render_application_markdown_structure():
    md = render_structured_document(
        "application",
        {
            "arbitration_commission": "北京市朝阳区劳动人事争议仲裁委员会",
            "applicant_name": "张三",
            "applicant_id": "110101199001011234",
            "applicant_address": "北京市朝阳区",
            "applicant_phone": "13800000000",
            "respondent_name": "某某科技有限公司",
            "respondent_address": "北京市海淀区",
            "respondent_legal_rep": "李四",
            "requests": "支付拖欠工资50000元\n支付经济补偿金10000元",
            "facts": "2020年1月入职，2024年6月起欠薪。",
            "legal_basis": "《劳动合同法》第三十八条、第四十六条。",
            "evidence": "劳动合同、工资流水。",
            "sign_date": "2024年12月1日",
        },
    )
    assert md.startswith("# 劳动仲裁申请书")
    assert "## 申请人" in md
    assert "## 仲裁请求" in md
    assert "1. 支付拖欠工资" in md
    assert "此致" in md
    assert "**姓名**" in md


def test_seed_from_parsed_case():
    seed = seed_from_parsed_case(
        {
            "parties": {
                "plaintiff": {"name": "王五", "identity": "320404200405032134"},
                "defendant": {"name": "甲公司"},
            },
            "claims": ["支付工资", "经济补偿"],
            "facts": "事实概要",
        }
    )
    assert seed["applicant_name"] == "王五"
    assert seed["respondent_name"] == "甲公司"
    assert "支付工资" in seed["requests"]


def test_render_complaint():
    md = render_structured_document(
        "complaint",
        {
            "court_name": "北京市海淀区人民法院",
            "plaintiff_name": "张三",
            "plaintiff_id": "110101199001011234",
            "plaintiff_address": "北京市",
            "defendant_name": "甲公司",
            "defendant_address": "北京市海淀区",
            "arbitration_info": "经××仲裁委裁决，不服裁决提起本案诉讼。",
            "claims": "判令被告支付工资",
            "facts": "事实与理由正文",
            "evidence": "证据一：劳动合同",
            "sign_date": "2024年12月1日",
        },
    )
    assert "# 民事起诉状" in md
    assert "## 劳动仲裁前置程序" in md
    assert has_structured_renderer("complaint")
