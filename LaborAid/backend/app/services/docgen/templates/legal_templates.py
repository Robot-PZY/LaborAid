"""预定义法律文书模板 — 法律文本由律师撰写，AI 只填充变量。

设计原则：
1. 模板中的法律文本是固定的、规范的，不依赖 LLM 生成
2. AI 只负责从案情中提取变量值填入模板
3. 变量缺失时显示 [待填写]，不编造
4. 保留旧字段兼容：如果模板变量未填充，回退到旧字段
"""

# ============================================================
# 劳动仲裁申请书 — 事实与理由模板
# 格式参考：标准劳动仲裁申请书范本（舟山市劳动争议仲裁委员会）
# ============================================================
APPLICATION_FACTS_TEMPLATE = """
申请人于{hire_year}年{hire_month}月入职被申请人处，担任{job_position}岗位，双方约定月工资标准为人民币{monthly_salary}元（大写：{monthly_salary_cn}）。{contract_info}工作地点位于{work_location}。{social_insurance_info}

自{dispute_start}起至{dispute_end}止，被申请人未依法足额支付劳动报酬，累计拖欠工资金额为人民币{arrears_amount}元（大写：{arrears_amount_cn}）。{dispute_details}

依据《中华人民共和国劳动争议调解仲裁法》第二条、第五条，《中华人民共和国劳动合同法》第三十条、第三十八条、第四十六条、第四十七条、第八十二条、第八十七条之规定，被申请人作为用人单位，应当依法向劳动者按时足额支付劳动报酬。被申请人拖欠劳动报酬的行为已构成违法，应当承担相应的法律责任。{legal_analysis_expansion}
"""

# ============================================================
# 民事起诉状 — 事实与理由模板
# ============================================================
COMPLAINT_FACTS_TEMPLATE = """
原告于{hire_year}年{hire_month}月入职被告处，担任{job_position}岗位，月工资标准为人民币{monthly_salary}元（大写：{monthly_salary_cn}）。{contract_info}

原告于{arbitration_apply_date}向{arbitration_commission}申请劳动仲裁。该委于{arbitration_ruling_date}作出{arbitration_case_number}号裁决书，裁决结果为：{arbitration_ruling_result}。{arbitration_dissatisfaction_reason}

{dispute_details}

{legal_analysis_expansion}
"""

# ============================================================
# 劳动监察投诉书 — 事实经过模板
# ============================================================
LABOR_SUPERVISION_FACTS_TEMPLATE = """
投诉人于{hire_year}年{hire_month}月入职被投诉单位，担任{job_position}岗位，约定月工资标准为人民币{monthly_salary}元（大写：{monthly_salary_cn}）。{contract_info}

自{dispute_start}起至{dispute_end}止，被投诉单位存在以下违法行为：{dispute_details}

投诉人多次与被投诉单位协商，要求其依法支付拖欠工资/补缴社会保险/支付加班费等，但被投诉单位均以各种理由推诿，至今未予解决。
"""

# ============================================================
# 模板注册表
# ============================================================
FACTS_TEMPLATES: dict[str, str] = {
    "application": APPLICATION_FACTS_TEMPLATE,
    "complaint": COMPLAINT_FACTS_TEMPLATE,
    "labor_supervision": LABOR_SUPERVISION_FACTS_TEMPLATE,
}

# 各模板需要的变量清单
TEMPLATE_VARIABLES: dict[str, list[str]] = {
    "application": [
        "hire_year", "hire_month", "job_position", "monthly_salary",
        "monthly_salary_cn", "contract_info", "work_location",
        "social_insurance_info", "dispute_start", "dispute_end",
        "arrears_amount", "arrears_amount_cn", "dispute_details",
        "legal_analysis_expansion",
    ],
    "complaint": [
        "hire_year", "hire_month", "job_position", "monthly_salary",
        "monthly_salary_cn", "contract_info",
        "arbitration_apply_date", "arbitration_commission",
        "arbitration_ruling_date", "arbitration_case_number",
        "arbitration_ruling_result", "arbitration_dissatisfaction_reason",
        "dispute_details", "legal_analysis_expansion",
    ],
    "labor_supervision": [
        "hire_year", "hire_month", "job_position", "monthly_salary",
        "monthly_salary_cn", "contract_info",
        "dispute_start", "dispute_end", "dispute_details",
    ],
}

# 模板变量的中文说明（用于 prompt 中引导 LLM 提取）
TEMPLATE_VARIABLE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "application": {
        "hire_year": "入职年份，如2023",
        "hire_month": "入职月份，如3",
        "job_position": "工作岗位，如钢筋工、保洁员、厨师等",
        "monthly_salary": "月工资标准（阿拉伯数字，如8000）",
        "monthly_salary_cn": "月工资中文大写（如捌仟元整）",
        "contract_info": "劳动合同签订情况（一句话，如：双方未签订书面劳动合同 / 双方签订了期限为X年的书面劳动合同）",
        "work_location": "工作地点（如：江苏省南京市XX区XX工地）",
        "social_insurance_info": "社保缴纳情况（一句话，如：被申请人未依法为申请人缴纳社会保险 / 被申请人仅缴纳了部分社会保险）",
        "dispute_start": "欠薪/争议起始时间，格式XXXX年XX月",
        "dispute_end": "欠薪/争议结束时间，格式XXXX年XX月",
        "arrears_amount": "拖欠工资金额（阿拉伯数字，如24000）",
        "arrears_amount_cn": "拖欠工资金额中文大写（如贰万肆仟元整）",
        "dispute_details": "争议经过详细描述（按时间线叙述每个关键事件：时间、地点、人物、经过、结果，不少于200字）",
        "legal_analysis_expansion": "结合本案事实的法律分析补充论述（引用法条后对应本案事实，不少于150字）",
    },
    "complaint": {
        "hire_year": "入职年份",
        "hire_month": "入职月份",
        "job_position": "工作岗位",
        "monthly_salary": "月工资标准（阿拉伯数字）",
        "monthly_salary_cn": "月工资中文大写",
        "contract_info": "劳动合同签订情况",
        "arbitration_apply_date": "申请仲裁日期，格式XXXX年XX月XX日",
        "arbitration_commission": "仲裁机构全称",
        "arbitration_ruling_date": "裁决日期，格式XXXX年XX月XX日",
        "arbitration_case_number": "仲裁案号",
        "arbitration_ruling_result": "裁决结果摘要",
        "arbitration_dissatisfaction_reason": "不服裁决的理由（不少于100字）",
        "dispute_details": "争议经过详细描述（按时间线，不少于200字）",
        "legal_analysis_expansion": "结合本案事实的法律分析（不少于150字）",
    },
    "labor_supervision": {
        "hire_year": "入职年份",
        "hire_month": "入职月份",
        "job_position": "工作岗位",
        "monthly_salary": "月工资标准（阿拉伯数字）",
        "monthly_salary_cn": "月工资中文大写",
        "contract_info": "劳动合同签订情况",
        "dispute_start": "违法事实起始时间",
        "dispute_end": "违法事实结束时间",
        "dispute_details": "违法事实详细描述（按时间线，不少于200字）",
    },
}


def get_facts_template(doc_type: str) -> str | None:
    """获取文书类型对应的事实与理由模板。"""
    return FACTS_TEMPLATES.get(doc_type)


def get_template_variables(doc_type: str) -> list[str]:
    """获取模板需要的变量清单。"""
    return TEMPLATE_VARIABLES.get(doc_type, [])


def get_variable_descriptions(doc_type: str) -> dict[str, str]:
    """获取模板变量的中文说明。"""
    return TEMPLATE_VARIABLE_DESCRIPTIONS.get(doc_type, {})


def render_facts_from_template(doc_type: str, payload: dict[str, str]) -> str:
    """用模板渲染事实与理由部分。变量缺失时显示[待填写]。"""
    from app.services.docgen.structured.helpers import PLACEHOLDER

    template = get_facts_template(doc_type)
    if not template:
        return ""

    variables = get_template_variables(doc_type)
    kwargs: dict[str, str] = {}
    for var in variables:
        val = payload.get(var, "")
        if not val or not val.strip():
            kwargs[var] = PLACEHOLDER
        else:
            kwargs[var] = val.strip()

    try:
        return template.format(**kwargs)
    except KeyError as e:
        # 模板中有变量但 payload 中没有，回退
        return ""
