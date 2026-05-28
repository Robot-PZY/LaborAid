"""结构化文书 → 固定 Markdown（多模板，版式由程序保证）。"""

from __future__ import annotations

from typing import Any, Callable

from app.services.docgen.structured.helpers import (
    md_field,
    md_fields_block,
    md_numbered_list,
    md_paragraphs,
    md_section,
    md_sign_arbitration,
    md_sign_court,
    md_sign_letter,
    md_title,
    val,
)


def render_application(d: dict[str, Any]) -> str:
    parts = [
        md_title("劳动仲裁申请书"),
        md_section(
            "申请人",
            md_fields_block([
                ("姓名", val(d, "applicant_name")),
                ("身份证号", val(d, "applicant_id")),
                ("住址", val(d, "applicant_address")),
                ("联系电话", val(d, "applicant_phone")),
            ]),
        ),
        md_section(
            "被申请人",
            md_fields_block([
                ("名称", val(d, "respondent_name")),
                ("住所地", val(d, "respondent_address")),
                ("法定代表人", val(d, "respondent_legal_rep", "—")),
            ]),
        ),
        md_section("仲裁请求", md_numbered_list(d.get("requests"))),
        md_section(
            "事实与理由",
            md_paragraphs(val(d, "facts"))
            + "\n\n### 法律依据\n\n"
            + md_paragraphs(val(d, "legal_basis")),
        ),
        md_section("证据目录", md_paragraphs(val(d, "evidence"))),
        md_sign_arbitration(val(d, "arbitration_commission"), date=val(d, "sign_date")),
    ]
    return "".join(parts)


def render_labor_supervision(d: dict[str, Any]) -> str:
    return (
        md_title("劳动监察投诉书")
        + md_section(
            "投诉人",
            md_fields_block([
                ("姓名", val(d, "complainant_name")),
                ("身份证号", val(d, "complainant_id")),
                ("联系电话", val(d, "complainant_phone")),
            ]),
        )
        + md_section(
            "被投诉单位",
            md_fields_block([
                ("单位名称", val(d, "employer_name")),
                ("地址", val(d, "employer_address")),
            ]),
        )
        + md_section("投诉事项", md_paragraphs(val(d, "items")))
        + md_section("事实经过", md_paragraphs(val(d, "facts")))
        + md_section("证据说明", md_paragraphs(val(d, "evidence")))
        + md_section("请求查处事项", md_paragraphs(val(d, "relief")))
        + f"\n投诉人：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_wage_demand_letter(d: dict[str, Any]) -> str:
    employer = val(d, "employer_name")
    return (
        md_title("工资催告函")
        + f"致：{employer}\n\n"
        + md_section("劳动关系", md_paragraphs(val(d, "employment")))
        + md_section("欠薪事实", md_paragraphs(val(d, "arrears")))
        + md_section(
            "催告事项",
            f"请贵单位于收到本函之日起 **{val(d, 'deadline')}** 内，将上述拖欠工资足额支付至本人。"
            "逾期不付，本人将依法向劳动监察部门投诉、申请劳动仲裁或提起诉讼，追究贵单位法律责任。\n",
        )
        + md_sign_letter(employer, signer="劳动者", date=val(d, "sign_date"))
    )


def render_forced_termination_notice(d: dict[str, Any]) -> str:
    employer = val(d, "employer_name")
    return (
        md_title("被迫解除劳动合同通知书")
        + f"致：{employer}\n\n"
        + md_section("用工事实", md_paragraphs(val(d, "facts")))
        + md_section(
            "解除依据",
            "现根据《中华人民共和国劳动合同法》第三十八条之规定，因贵单位存在下列情形：\n\n"
            + md_paragraphs(val(d, "article38_reasons"))
            + "\n本人现通知解除双方劳动合同。\n",
        )
        + md_section(
            "解除生效",
            f"本通知自送达之日起生效，解除日期：**{val(d, 'effective_date')}**。\n"
            "本人保留依法主张经济补偿、工资、加班费、未休年休假工资等权利。\n",
        )
        + md_sign_letter(employer, date=val(d, "sign_date"))
    )


def render_arbitration_authorization(d: dict[str, Any]) -> str:
    return (
        md_title("劳动仲裁代理委托书")
        + md_fields_block([
            ("委托人", val(d, "principal")),
            ("受托人", val(d, "agent")),
            ("受托人身份", val(d, "agent_capacity")),
        ])
        + md_section("代理权限", md_paragraphs(val(d, "scope")))
        + md_section("委托期限", md_paragraphs(val(d, "term")))
        + f"\n委托人：[签名]\n受托人：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_evidence_list(d: dict[str, Any]) -> str:
    ref = val(d, "case_ref", "—")
    return (
        md_title("证据清单")
        + md_fields_block([
            ("案号", ref),
            ("提交人", val(d, "submitter")),
        ])
        + md_section("证据目录", md_numbered_list(d.get("items")))
        + f"\n提交人：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_complaint(d: dict[str, Any]) -> str:
    parts = [
        md_title("民事起诉状"),
        md_section(
            "原告",
            md_fields_block([
                ("姓名", val(d, "plaintiff_name")),
                ("身份证号", val(d, "plaintiff_id")),
                ("住所地", val(d, "plaintiff_address")),
                ("联系电话", val(d, "plaintiff_phone", "—")),
            ]),
        ),
        md_section(
            "被告",
            md_fields_block([
                ("名称", val(d, "defendant_name")),
                ("住所地", val(d, "defendant_address")),
                ("法定代表人", val(d, "defendant_legal_rep", "—")),
            ]),
        ),
        md_section("劳动仲裁前置程序", md_paragraphs(val(d, "arbitration_info"))),
        md_section("诉讼请求", md_numbered_list(d.get("claims"))),
        md_section("事实与理由", md_paragraphs(val(d, "facts"))),
        md_section("证据清单", md_paragraphs(val(d, "evidence"))),
    ]
    med = val(d, "mediation_willing", "")
    if med and med != "—":
        parts.append(md_section("调解意愿", f"是否同意先行调解：**{med}**\n"))
    parts.append(md_sign_court(val(d, "court_name"), date=val(d, "sign_date")))
    return "".join(parts)


def render_answer(d: dict[str, Any]) -> str:
    return (
        md_title("答辩状")
        + md_fields_block([
            ("案号", val(d, "case_number")),
            ("答辩人", val(d, "respondent_name")),
        ])
        + md_section("答辩意见", md_numbered_list(d.get("defense_points")))
        + md_section("事实与理由", md_paragraphs(val(d, "facts")))
        + md_sign_court(val(d, "court_name"), signer_label="答辩人", date=val(d, "sign_date"))
    )


def render_appeal(d: dict[str, Any]) -> str:
    return (
        md_title("上诉状")
        + md_fields_block([
            ("上诉人", val(d, "appellant")),
            ("被上诉人", val(d, "appellee")),
        ])
        + md_section("一审信息", md_paragraphs(val(d, "first_instance")))
        + md_section("上诉请求", md_numbered_list(d.get("appeal_requests")))
        + md_section("上诉理由", md_paragraphs(val(d, "reasons")))
        + md_sign_court(val(d, "court_name"), signer_label="上诉人", date=val(d, "sign_date"))
    )


def render_agency_opinion(d: dict[str, Any]) -> str:
    return (
        md_title("代理词")
        + f"审判长、审判员：\n\n{md_paragraphs(val(d, 'agent_info'))}\n"
        + md_section("一、事实认定意见", md_paragraphs(val(d, "facts_opinion")))
        + md_section("二、法律适用意见", md_paragraphs(val(d, "law_opinion")))
        + md_section("三、争议焦点分析", md_paragraphs(val(d, "focus")))
        + md_section("四、代理意见", md_paragraphs(val(d, "conclusion")))
        + "\n综上所述，恳请法庭依法支持我方诉讼/仲裁请求。\n\n"
        + f"代理人：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_legal_opinion(d: dict[str, Any]) -> str:
    return (
        md_title("法律意见书")
        + f"致：{val(d, 'recipient')}\n\n"
        + md_section("一、事实背景", md_paragraphs(val(d, "background")))
        + md_section("二、法律分析", md_paragraphs(val(d, "analysis")))
        + md_section("三、结论意见", md_paragraphs(val(d, "opinion")))
        + "\n（本意见书仅供参考，不构成正式法律意见。）\n\n"
        + f"出具人：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_lawyer_letter(d: dict[str, Any]) -> str:
    return (
        md_title("律师函")
        + md_fields_block([
            ("收函人", val(d, "recipient")),
            ("律师事务所", val(d, "law_firm")),
        ])
        + md_section("事实陈述", md_paragraphs(val(d, "facts")))
        + md_section("律师要求", md_paragraphs(val(d, "demands")))
        + md_section("法律后果", md_paragraphs(val(d, "consequences")))
        + "\n特此函告。\n\n"
        + f"{val(d, 'law_firm')}\n律师：[签名]\n{val(d, 'sign_date')}\n"
    )


def render_preservation_application(d: dict[str, Any]) -> str:
    return (
        md_title("财产保全申请书")
        + md_fields_block([
            ("申请人", val(d, "applicant")),
            ("被申请人", val(d, "respondent")),
        ])
        + md_section("请求事项", md_paragraphs(val(d, "preservation_target")))
        + md_section("事实与理由", md_paragraphs(val(d, "reasons")))
        + md_section("担保情况", md_paragraphs(val(d, "guarantee")))
        + md_sign_court(val(d, "court_name"), signer_label="申请人", date=val(d, "sign_date"))
    )


def render_labor_contract(d: dict[str, Any]) -> str:
    return (
        md_title("劳动合同")
        + md_section(
            "合同双方",
            md_fields_block([
                ("甲方（用人单位）", val(d, "employer_name")),
                ("甲方住所", val(d, "employer_address")),
                ("法定代表人", val(d, "employer_rep")),
                ("乙方（劳动者）", val(d, "employee_name")),
                ("乙方身份证号", val(d, "employee_id")),
                ("乙方住址", val(d, "employee_address")),
            ]),
        )
        + md_section(
            "一、合同期限",
            md_fields_block([
                ("期限类型", val(d, "term_type")),
                ("起止日期/工作任务", val(d, "term_dates")),
                ("试用期", val(d, "probation", "无")),
            ]),
        )
        + md_section(
            "二、工作内容与地点",
            md_fields_block([
                ("工作岗位", val(d, "job_position")),
                ("工作地点", val(d, "work_location")),
            ])
            + md_paragraphs(val(d, "job_duties")),
        )
        + md_section(
            "三、工作时间和休息休假",
            md_fields_block([("工时制度", val(d, "work_hours"))])
            + md_paragraphs(val(d, "rest_leave")),
        )
        + md_section(
            "四、劳动报酬",
            md_paragraphs(val(d, "wage_standard"))
            + f"\n**支付日期**：{val(d, 'pay_date')}\n",
        )
        + md_section(
            "五、社会保险和福利",
            md_paragraphs(val(d, "social_insurance"))
            + (f"\n**福利**：{val(d, 'benefits')}\n" if val(d, "benefits", "") not in ("", "—", "[待填写]") else ""),
        )
        + md_section("六、劳动保护", md_paragraphs(val(d, "labor_protection")))
        + md_section(
            "七、其他约定",
            md_paragraphs(
                "\n".join(
                    x
                    for x in [
                        f"保密/竞业：{val(d, 'confidentiality', '')}" if val(d, "confidentiality", "") not in ("", "—", "[待填写]") else "",
                        f"培训服务期：{val(d, 'training', '')}" if val(d, "training", "") not in ("", "—", "[待填写]") else "",
                        f"送达地址：{val(d, 'delivery_address', '')}" if val(d, "delivery_address", "") not in ("", "—", "[待填写]") else "",
                    ]
                    if x
                )
            )
            or "无特别约定。\n",
        )
        + md_section("八、合同变更、解除、终止", md_paragraphs(val(d, "change_termination")))
        + md_section("九、劳动争议处理", md_paragraphs(val(d, "dispute_resolution")))
        + f"\n甲方（盖章）：________　　乙方（签字）：________\n签订日期：{val(d, 'sign_date')}\n"
    )


def render_contract(d: dict[str, Any]) -> str:
    return (
        md_title("合同")
        + md_fields_block([
            ("甲方", val(d, "party_a")),
            ("乙方", val(d, "party_b")),
        ])
        + md_section("一、合同标的", md_paragraphs(val(d, "subject")))
        + md_section("二、价款及支付", md_paragraphs(val(d, "price")))
        + md_section("三、履行", md_paragraphs(val(d, "performance")))
        + md_section("四、违约责任", md_paragraphs(val(d, "breach")))
        + md_section("五、争议解决", md_paragraphs(val(d, "dispute")))
        + f"\n甲方（签字）：________　　乙方（签字）：________\n签订日期：{val(d, 'sign_date')}\n"
    )


def render_mediation(d: dict[str, Any]) -> str:
    return (
        md_title("劳动争议调解协议书")
        + md_fields_block([
            ("调解组织", val(d, "mediation_org")),
            ("劳动者", val(d, "party_worker")),
            ("用人单位", val(d, "party_employer")),
        ])
        + md_section("争议概述", md_paragraphs(val(d, "dispute_summary")))
        + md_section("履行方案", md_paragraphs(val(d, "payment")))
        + md_section("其他义务", md_paragraphs(val(d, "other_obligations", "无")))
        + md_section("终局条款", md_paragraphs(val(d, "finality")))
        + md_section("违约责任", md_paragraphs(val(d, "breach_liability")))
        + md_section("生效条件", md_paragraphs(val(d, "effective_clause")))
        + f"\n劳动者（签字）：________　用人单位（盖章）：________\n调解员：________\n{val(d, 'sign_date')}\n"
    )


def render_settlement_agreement(d: dict[str, Any]) -> str:
    return (
        md_title("劳动争议和解协议")
        + md_fields_block([
            ("甲方（用人单位）", val(d, "employer")),
            ("乙方（劳动者）", val(d, "worker")),
        ])
        + md_section("一、和解对价", md_paragraphs(val(d, "settlement_amount")))
        + md_section("二、支付安排", md_paragraphs(val(d, "payment_terms")))
        + md_section("三、权利义务", md_paragraphs(val(d, "mutual_release")))
        + md_section("四、违约责任", md_paragraphs(val(d, "breach")))
        + f"\n甲方（盖章）：________　　乙方（签字）：________\n签订日期：{val(d, 'sign_date')}\n"
    )


def render_structured_document(doc_type: str, payload: dict[str, Any]) -> str:
    renderer = RENDERERS.get(doc_type)
    if not renderer:
        raise ValueError(f"No structured renderer for doc_type={doc_type}")
    return renderer(payload)


RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "application": render_application,
    "labor_supervision": render_labor_supervision,
    "wage_demand_letter": render_wage_demand_letter,
    "forced_termination_notice": render_forced_termination_notice,
    "arbitration_authorization": render_arbitration_authorization,
    "evidence_list": render_evidence_list,
    "complaint": render_complaint,
    "answer": render_answer,
    "appeal": render_appeal,
    "agency_opinion": render_agency_opinion,
    "legal_opinion": render_legal_opinion,
    "lawyer_letter": render_lawyer_letter,
    "preservation_application": render_preservation_application,
    "labor_contract": render_labor_contract,
    "contract": render_contract,
    "mediation": render_mediation,
    "settlement_agreement": render_settlement_agreement,
}
