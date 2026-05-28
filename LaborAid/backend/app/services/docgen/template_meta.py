"""平台文书模板元数据（分类、是否结构化）。"""

from __future__ import annotations

TEMPLATE_CATEGORIES: dict[str, str] = {
    "application": "劳动维权",
    "labor_supervision": "劳动维权",
    "wage_demand_letter": "劳动维权",
    "forced_termination_notice": "劳动维权",
    "arbitration_authorization": "劳动维权",
    "evidence_list": "劳动维权",
    "labor_contract": "合同与调解",
    "mediation": "合同与调解",
    "settlement_agreement": "合同与调解",
    "complaint": "诉讼文书",
    "answer": "诉讼文书",
    "appeal": "诉讼文书",
    "agency_opinion": "诉讼文书",
    "legal_opinion": "诉讼文书",
    "lawyer_letter": "诉讼文书",
    "preservation_application": "诉讼文书",
    "contract": "合同与调解",
}


def supports_structured_generation(doc_type: str) -> bool:
    from app.services.docgen.structured.renderers import RENDERERS

    return doc_type in RENDERERS


def category_for_type(doc_type: str) -> str:
    return TEMPLATE_CATEGORIES.get(doc_type, "其他")
