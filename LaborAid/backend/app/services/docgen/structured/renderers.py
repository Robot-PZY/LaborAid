"""结构化文书 → 固定 Markdown（多模板，版式由程序保证）。"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.services.docgen.structured.helpers import (
    NO_INDENT,
    PLACEHOLDER,
    md_body_paragraphs,
    md_cn_section,
    md_evidence_table,
    md_field,
    md_fields_block,
    md_numbered_list,
    md_paragraphs,
    md_party_line,
    md_salutation,
    md_section,
    md_sign_arbitration,
    md_sign_court,
    md_sign_letter,
    md_sub_heading,
    md_title,
    val,
)

logger = logging.getLogger(__name__)


# 模板变量缺失时的友好提示映射
_TEMPLATE_VAR_HINTS: dict[str, str] = {
    "hire_year": "【入职年份待补充】",
    "hire_month": "【入职月份待补充】",
    "job_position": "【工作岗位待补充】",
    "monthly_salary": "【月工资待补充】",
    "monthly_salary_cn": "【月工资大写待补充】",
    "contract_info": "【合同签订情况待补充】",
    "work_location": "【工作地点待补充】",
    "social_insurance_info": "【社保缴纳情况待补充】",
    "dispute_start": "【争议起始时间待补充】",
    "dispute_end": "【争议结束时间待补充】",
    "arrears_amount": "【欠薪金额待补充】",
    "arrears_amount_cn": "【欠薪金额大写待补充】",
    "dispute_details": "【争议经过待补充】",
    "legal_analysis_expansion": "【法律分析待补充】",
}


def _render_facts_from_template(doc_type: str, d: dict[str, Any]) -> str:
    """用预定义法律文本模板渲染事实与理由部分。

    优先使用模板变量（hire_year, job_position 等），
    如果模板变量未填充，回退到旧字段（facts_employment, facts_dispute 等）。
    如果旧字段也为空，回退到 facts 整体字段。
    """
    try:
        from app.services.docgen.templates.legal_templates import (
            render_facts_from_template as _render,
            get_facts_template,
            get_template_variables,
        )
    except ImportError:
        return ""

    template = get_facts_template(doc_type)
    if not template:
        return ""

    # 收集模板变量
    variables = get_template_variables(doc_type)
    kwargs: dict[str, str] = {}
    all_empty = True
    for var in variables:
        v = val(d, var, "")
        if v and v != PLACEHOLDER:
            kwargs[var] = v.strip()
            all_empty = False
        else:
            # 使用友好提示而非通用占位符
            kwargs[var] = _TEMPLATE_VAR_HINTS.get(var, PLACEHOLDER)

    if all_empty:
        # 所有模板变量都为空 → 回退到旧字段
        return _fallback_facts_render(doc_type, d)

    try:
        return template.format(**kwargs)
    except KeyError:
        logger.warning("Template render failed for %s, falling back", doc_type)
        return _fallback_facts_render(doc_type, d)


def _fallback_facts_render(doc_type: str, d: dict[str, Any]) -> str:
    """旧字段回退渲染：兼容未使用模板变量的情况。"""
    parts: list[str] = []

    if doc_type == "application":
        employment = val(d, "facts_employment", "")
        dispute = val(d, "facts_dispute", "")
        employment_info = val(d, "employment_info", "")

        if employment_info and employment_info != PLACEHOLDER:
            parts.append(md_sub_heading("劳动关系基本情况") + md_body_paragraphs(employment_info))
        elif employment and employment != PLACEHOLDER:
            parts.append(md_sub_heading("劳动关系基本情况") + md_body_paragraphs(employment))

        if dispute and dispute != PLACEHOLDER:
            parts.append(md_sub_heading("争议事实经过") + md_body_paragraphs(dispute))
        elif employment and employment != PLACEHOLDER and not employment_info:
            parts.append(md_sub_heading("争议事实经过") + md_body_paragraphs(employment))

        social_ins = val(d, "social_insurance", "")
        if social_ins and social_ins != PLACEHOLDER:
            parts.append(md_sub_heading("社会保险缴纳情况") + md_body_paragraphs(social_ins))

        legal_analysis = val(d, "legal_analysis", "")
        if legal_analysis and legal_analysis != PLACEHOLDER:
            parts.append(md_sub_heading("法律分析") + md_body_paragraphs(legal_analysis))

        basis = val(d, "legal_basis", "")
        if basis and basis != PLACEHOLDER and basis != val(d, "facts"):
            parts.append(md_sub_heading("法律依据") + md_body_paragraphs(basis))

    elif doc_type == "complaint":
        emp_bg = val(d, "employment_background", "")
        if emp_bg and emp_bg != PLACEHOLDER:
            parts.append(md_sub_heading("劳动关系背景") + md_body_paragraphs(emp_bg))
        arb_facts = val(d, "facts_arbitration", "")
        if arb_facts and arb_facts != PLACEHOLDER:
            parts.append(md_sub_heading("仲裁阶段经过") + md_body_paragraphs(arb_facts))
        dispute = val(d, "facts_dispute", "")
        if dispute and dispute != PLACEHOLDER:
            parts.append(md_sub_heading("争议事实经过") + md_body_paragraphs(dispute))
        legal_analysis = val(d, "legal_analysis", "")
        if legal_analysis and legal_analysis != PLACEHOLDER:
            parts.append(md_sub_heading("法律分析") + md_body_paragraphs(legal_analysis))

    elif doc_type == "labor_supervision":
        employment_info = val(d, "employment_info", "")
        facts_text = val(d, "facts", "")
        if employment_info and employment_info != PLACEHOLDER:
            parts.append(md_sub_heading("劳动关系基本情况") + md_body_paragraphs(employment_info))
            if facts_text and facts_text != PLACEHOLDER:
                parts.append(md_sub_heading("投诉事实经过") + md_body_paragraphs(facts_text))
        else:
            parts.append(md_body_paragraphs(facts_text))

    # 最终回退：facts 整体字段
    if not parts:
        facts = val(d, "facts", "")
        if facts and facts != PLACEHOLDER:
            parts.append(md_body_paragraphs(facts))

    return "".join(parts) if parts else f"{PLACEHOLDER}\n"


def render_application(d: dict[str, Any]) -> str:
    respondent_fields = [
        ("名称", val(d, "respondent_name")),
        ("住所地", val(d, "respondent_address")),
        ("法定代表人", val(d, "respondent_legal_rep", "—")),
    ]
    usci = val(d, "respondent_usci", "")
    if usci and usci != PLACEHOLDER:
        respondent_fields.append(("统一社会信用代码", usci))

    # 事实与理由：优先模板渲染，回退旧字段
    facts_content = _render_facts_from_template("application", d)

    parts = [
        md_title("劳动仲裁申请书"),
        md_party_line("申请人", [
            ("姓名", val(d, "applicant_name")),
            ("身份证号", val(d, "applicant_id")),
            ("住址", val(d, "applicant_address")),
            ("联系电话", val(d, "applicant_phone")),
        ]),
        md_party_line("被申请人", respondent_fields),
        md_cn_section("一", "仲裁请求", md_numbered_list(d.get("requests"))),
        md_cn_section("二", "事实与理由", facts_content),
        md_cn_section("三", "证据目录", md_evidence_table(d.get("evidence"))),
        md_sign_arbitration(val(d, "arbitration_commission"), date=val(d, "sign_date")),
    ]
    return "".join(parts)


def render_labor_supervision(d: dict[str, Any]) -> str:
    # 事实经过：优先模板渲染，回退旧字段
    facts_content = _render_facts_from_template("labor_supervision", d)

    return (
        md_title("劳动监察投诉书")
        + md_party_line("投诉人", [
            ("姓名", val(d, "complainant_name")),
            ("身份证号", val(d, "complainant_id")),
            ("联系电话", val(d, "complainant_phone")),
            ("住址", val(d, "complainant_address", "—")),
        ])
        + md_party_line("被投诉用人单位", [
            ("名称", val(d, "employer_name")),
            ("地址", val(d, "employer_address")),
            ("法定代表人", val(d, "employer_legal_rep", val(d, "employer_rep", "—"))),
        ])
        + md_cn_section("一", "投诉事项", md_body_paragraphs(val(d, "items")))
        + md_cn_section("二", "事实经过", facts_content)
        + md_cn_section("三", "证据材料", md_evidence_table(d.get("evidence")))
        + md_cn_section("四", "请求事项", md_body_paragraphs(
            val(d, "relief") if val(d, "relief") not in ("", "—", "[待填写]")
            else "请求劳动监察部门依法查处被投诉单位违法行为，责令其限期改正并依法处理。"
        ))
        + f"{NO_INDENT}投诉人：（签名）\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_wage_demand_letter(d: dict[str, Any]) -> str:
    employer = val(d, "employer_name")
    return (
        md_title("工资催告函")
        + md_salutation(employer)
        + md_body_paragraphs(
            val(d, "employment") if val(d, "employment") != PLACEHOLDER
            else f"本人与贵单位存在劳动关系，现就工资支付事宜函告如下。"
        )
        + md_cn_section("一", "欠薪事实", md_body_paragraphs(val(d, "arrears")))
        + md_cn_section("二", "催告事项",
            f"请贵单位于收到本函之日起 **{val(d, 'deadline', '15日')}** 内，将上述拖欠工资足额支付至本人指定账户。"
            "逾期不付，本人将依法向劳动监察部门投诉、申请劳动仲裁或提起诉讼，追究贵单位法律责任。"
        )
        + md_sign_letter(employer, signer="劳动者", date=val(d, "sign_date"))
    )


def render_forced_termination_notice(d: dict[str, Any]) -> str:
    employer = val(d, "employer_name")
    worker = val(d, "worker", val(d, "applicant_name", "劳动者"))
    emp_id = val(d, "employee_id", val(d, "applicant_id"))
    intro = (
        f"本人{worker}（身份证号：{emp_id}）与贵单位存在劳动关系。"
        f"{val(d, 'facts')}"
    )
    return (
        md_title("被迫解除劳动合同通知书")
        + md_salutation(employer)
        + md_body_paragraphs(intro)
        + md_cn_section(
            "一",
            "解除依据",
            "现依据《中华人民共和国劳动合同法》第三十八条之规定，因贵单位存在下列违法/违约情形：\n\n"
            + md_body_paragraphs(val(d, "article38_reasons"))
            + f"\n{NO_INDENT}本人现正式通知解除双方劳动合同。\n",
        )
        + md_cn_section(
            "二",
            "解除生效及权利保留",
            f"本通知自送达之日起生效，劳动合同解除日期为 **{val(d, 'effective_date', val(d, 'sign_date'))}**。"
            "本人保留依法主张经济补偿、补发工资、加班费、未休年休假工资、社会保险损失等全部合法权利。\n",
        )
        + md_sign_letter(employer, signer=worker, date=val(d, "sign_date"))
    )


def render_arbitration_authorization(d: dict[str, Any]) -> str:
    return (
        md_title("劳动仲裁代理委托书")
        + md_party_line("委托人", [
            ("姓名", val(d, "principal")),
            ("身份证号", val(d, "applicant_id", "—")),
            ("住址", val(d, "applicant_address", "—")),
        ])
        + md_party_line("受托人", [
            ("姓名", val(d, "agent")),
            ("身份", val(d, "agent_capacity")),
        ])
        + md_cn_section("一", "委托事项", "代为参加与本案有关的劳动仲裁活动，包括但不限于提交材料、参加庭审、签收法律文书等。")
        + md_cn_section("二", "代理权限", md_body_paragraphs(val(d, "scope")))
        + md_cn_section("三", "委托期限", md_body_paragraphs(val(d, "term", "自签署之日起至本案仲裁程序终结之日止。")))
        + f"{NO_INDENT}委托人：（签名）\n{NO_INDENT}受托人：（签名）\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_evidence_list(d: dict[str, Any]) -> str:
    ref = val(d, "case_ref", "—")
    return (
        md_title("证据清单")
        + md_party_line("提交人", [("姓名/名称", val(d, "submitter"))])
        + (f"{NO_INDENT}案号/案由：{ref}\n\n" if ref and ref != "—" else "")
        + md_cn_section("一", "证据目录", md_evidence_table(d.get("items")))
        + f"{NO_INDENT}提交人：（签名）\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_complaint(d: dict[str, Any]) -> str:
    defendant_fields = [
        ("名称", val(d, "defendant_name")),
        ("住所地", val(d, "defendant_address")),
        ("法定代表人", val(d, "defendant_legal_rep", "—")),
    ]
    usci = val(d, "defendant_usci", "")
    if usci and usci != PLACEHOLDER:
        defendant_fields.append(("统一社会信用代码", usci))

    # 事实与理由：优先模板渲染，回退旧字段
    facts_content = _render_facts_from_template("complaint", d)

    parts = [
        md_title("民事起诉状"),
        md_party_line("原告", [
            ("姓名", val(d, "plaintiff_name")),
            ("身份证号", val(d, "plaintiff_id")),
            ("住所地", val(d, "plaintiff_address")),
            ("联系电话", val(d, "plaintiff_phone", "—")),
        ]),
        md_party_line("被告", defendant_fields),
        md_cn_section("一", "劳动仲裁前置程序", md_body_paragraphs(val(d, "arbitration_info"))),
        md_cn_section("二", "诉讼请求", md_numbered_list(d.get("claims"))),
        md_cn_section("三", "事实与理由", facts_content),
        md_cn_section("四", "证据目录", md_evidence_table(d.get("evidence"))),
    ]
    med = val(d, "mediation_willing", "")
    if med and med != "—":
        parts.append(md_cn_section("五", "调解意愿", f"是否同意先行调解：**{med}**"))
    parts.append(md_sign_court(val(d, "court_name"), date=val(d, "sign_date")))
    return "".join(parts)


def render_answer(d: dict[str, Any]) -> str:
    return (
        md_title("答辩状")
        + md_fields_block([
            ("案号", val(d, "case_number")),
            ("答辩人", val(d, "respondent_name")),
        ])
        + md_cn_section("一", "答辩意见", md_numbered_list(d.get("defense_points")))
        + md_cn_section("二", "事实与理由", md_body_paragraphs(val(d, "facts")))
        + md_sign_court(val(d, "court_name"), signer_label="答辩人", date=val(d, "sign_date"))
    )


def render_appeal(d: dict[str, Any]) -> str:
    return (
        md_title("上诉状")
        + md_party_line("上诉人", [("姓名/名称", val(d, "appellant"))])
        + md_party_line("被上诉人", [("姓名/名称", val(d, "appellee"))])
        + md_cn_section("一", "一审信息", md_body_paragraphs(val(d, "first_instance")))
        + md_cn_section("二", "上诉请求", md_numbered_list(d.get("appeal_requests")))
        + md_cn_section("三", "上诉理由", md_body_paragraphs(val(d, "reasons")))
        + md_sign_court(val(d, "court_name"), signer_label="上诉人", date=val(d, "sign_date"))
    )


def render_agency_opinion(d: dict[str, Any]) -> str:
    return (
        md_title("代理词")
        + f"{NO_INDENT}审判长、审判员：\n\n"
        + md_body_paragraphs(val(d, "agent_info"))
        + md_cn_section("一", "事实认定意见", md_body_paragraphs(val(d, "facts_opinion")))
        + md_cn_section("二", "法律适用意见", md_body_paragraphs(val(d, "law_opinion")))
        + md_cn_section("三", "争议焦点分析", md_body_paragraphs(val(d, "focus")))
        + md_cn_section("四", "代理意见", md_body_paragraphs(val(d, "conclusion")))
        + f"{NO_INDENT}综上所述，恳请法庭依法支持我方诉讼/仲裁请求。\n\n"
        + f"{NO_INDENT}代理人：（签名）\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_legal_opinion(d: dict[str, Any]) -> str:
    return (
        md_title("法律意见书")
        + md_salutation(val(d, "recipient"))
        + md_cn_section("一", "事实背景", md_body_paragraphs(val(d, "background")))
        + md_cn_section("二", "法律分析", md_body_paragraphs(val(d, "analysis")))
        + md_cn_section("三", "结论意见", md_body_paragraphs(val(d, "opinion")))
        + f"{NO_INDENT}（本意见书仅供参考，不构成正式法律意见。）\n\n"
        + f"{NO_INDENT}出具人：（签名）\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_lawyer_letter(d: dict[str, Any]) -> str:
    return (
        md_title("律师函")
        + md_party_line("收函人", [("名称", val(d, "recipient"))])
        + md_party_line("律师事务所", [("名称", val(d, "law_firm"))])
        + md_cn_section("一", "事实陈述", md_body_paragraphs(val(d, "facts")))
        + md_cn_section("二", "律师要求", md_body_paragraphs(val(d, "demands")))
        + md_cn_section("三", "法律后果", md_body_paragraphs(val(d, "consequences")))
        + md_sign_letter(val(d, "recipient"), signer=f"{val(d, 'law_firm')} 律师", date=val(d, "sign_date"))
    )


def render_preservation_application(d: dict[str, Any]) -> str:
    return (
        md_title("财产保全申请书")
        + md_party_line("申请人", [("姓名/名称", val(d, "applicant"))])
        + md_party_line("被申请人", [("姓名/名称", val(d, "respondent"))])
        + md_cn_section("一", "请求事项", md_body_paragraphs(val(d, "preservation_target")))
        + md_cn_section("二", "事实与理由", md_body_paragraphs(val(d, "reasons")))
        + md_cn_section("三", "担保情况", md_body_paragraphs(val(d, "guarantee")))
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
        + md_cn_section(
            "一",
            "合同期限",
            md_fields_block([
                ("期限类型", val(d, "term_type")),
                ("起止日期/工作任务", val(d, "term_dates")),
                ("试用期", val(d, "probation", "无")),
            ]),
        )
        + md_cn_section(
            "二",
            "工作内容与地点",
            md_fields_block([
                ("工作岗位", val(d, "job_position")),
                ("工作地点", val(d, "work_location")),
            ])
            + md_body_paragraphs(val(d, "job_duties")),
        )
        + md_cn_section(
            "三",
            "工作时间和休息休假",
            md_fields_block([("工时制度", val(d, "work_hours"))])
            + md_body_paragraphs(val(d, "rest_leave")),
        )
        + md_cn_section(
            "四",
            "劳动报酬",
            md_body_paragraphs(val(d, "wage_standard"))
            + f"\n**支付日期**：{val(d, 'pay_date')}\n",
        )
        + md_cn_section(
            "五",
            "社会保险和福利",
            md_body_paragraphs(val(d, "social_insurance"))
            + (f"\n**福利**：{val(d, 'benefits')}\n" if val(d, "benefits", "") not in ("", "—", "[待填写]") else ""),
        )
        + md_cn_section("六", "劳动保护", md_body_paragraphs(val(d, "labor_protection")))
        + md_cn_section(
            "七",
            "其他约定",
            md_body_paragraphs(
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
        + md_cn_section("八", "合同变更、解除、终止", md_body_paragraphs(val(d, "change_termination")))
        + md_cn_section("九", "劳动争议处理", md_body_paragraphs(val(d, "dispute_resolution")))
        + f"\n{NO_INDENT}甲方（盖章）：________　　乙方（签字）：________\n{NO_INDENT}签订日期：{val(d, 'sign_date')}\n"
    )


def render_contract(d: dict[str, Any]) -> str:
    return (
        md_title("合同")
        + md_party_line("甲方", [("名称", val(d, "party_a"))])
        + md_party_line("乙方", [("名称", val(d, "party_b"))])
        + md_cn_section("一", "合同标的", md_body_paragraphs(val(d, "subject")))
        + md_cn_section("二", "价款及支付", md_body_paragraphs(val(d, "price")))
        + md_cn_section("三", "履行", md_body_paragraphs(val(d, "performance")))
        + md_cn_section("四", "违约责任", md_body_paragraphs(val(d, "breach")))
        + md_cn_section("五", "争议解决", md_body_paragraphs(val(d, "dispute")))
        + f"\n{NO_INDENT}甲方（签字）：________　　乙方（签字）：________\n{NO_INDENT}签订日期：{val(d, 'sign_date')}\n"
    )


def render_mediation(d: dict[str, Any]) -> str:
    return (
        md_title("劳动争议调解协议书")
        + md_party_line("调解组织", [("名称", val(d, "mediation_org"))])
        + md_party_line("劳动者", [("姓名", val(d, "party_worker"))])
        + md_party_line("用人单位", [("名称", val(d, "party_employer"))])
        + md_cn_section("一", "争议概述", md_body_paragraphs(val(d, "dispute_summary")))
        + md_cn_section("二", "履行方案", md_body_paragraphs(val(d, "payment")))
        + md_cn_section("三", "其他义务", md_body_paragraphs(val(d, "other_obligations", "无")))
        + md_cn_section("四", "终局条款", md_body_paragraphs(val(d, "finality")))
        + md_cn_section("五", "违约责任", md_body_paragraphs(val(d, "breach_liability")))
        + md_cn_section("六", "生效条件", md_body_paragraphs(val(d, "effective_clause")))
        + f"\n{NO_INDENT}劳动者（签字）：________　用人单位（盖章）：________\n{NO_INDENT}调解员：________\n{NO_INDENT}{val(d, 'sign_date')}\n"
    )


def render_settlement_agreement(d: dict[str, Any]) -> str:
    return (
        md_title("劳动争议和解协议")
        + md_party_line("甲方（用人单位）", [("名称", val(d, "employer"))])
        + md_party_line("乙方（劳动者）", [("姓名", val(d, "worker"))])
        + md_cn_section("一", "和解对价", md_body_paragraphs(val(d, "settlement_amount")))
        + md_cn_section("二", "支付安排", md_body_paragraphs(val(d, "payment_terms")))
        + md_cn_section("三", "权利义务", md_body_paragraphs(val(d, "mutual_release")))
        + md_cn_section("四", "违约责任", md_body_paragraphs(val(d, "breach")))
        + f"\n{NO_INDENT}甲方（盖章）：________　　乙方（签字）：________\n{NO_INDENT}签订日期：{val(d, 'sign_date')}\n"
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
