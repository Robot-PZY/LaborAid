"""
平台文书模板全集（劳动者 + 民事 + 合同/调解）。

依据：
- 人社部《劳动合同（通用）》示范文本（劳动合同法第十七条必备条款）
- 最高人民法院等《部分案件起诉状答辩状示范文本》（要素式，含劳动争议纠纷）
- 《劳动争议调解仲裁法》第十四条调解协议书

用法:
    python -m templates.seed_platform_pack
"""

from __future__ import annotations

from app.services.docgen.structured.renderers import RENDERERS
from app.services.docgen.template_structure import structure_to_variables

STRUCTURED_DOC_TYPES = frozenset(RENDERERS.keys())
from templates.seed_utils import COMMON_FORMAT, seed_template_records

_FMT = COMMON_FORMAT

_TEMPLATE_OUTPUT_RULES = """
【输出规范 — 自由撰写模式】
1. 仅输出可直接提交的 Markdown 正文，第一行必须是 # 文书标题。
2. 禁止问候、禁止自我介绍、禁止出现劳权智助/LaborAid/AI 等字样。
3. 使用 ## 一级节、### 二级节；当事人字段用 **标签**：值。
4. 仲裁请求、证据等用 1. 2. 3. 有序列表分项。
5. 缺失信息用 [待填写]，不得编造与案情冲突的内容。
"""

_STRUCTURED_EXTRACTION_HINT = """
【结构化生成 — 字段抽取】
系统将根据下方 structure.sections 中的字段键自动拼版为正式 Markdown（固定章节与 Word 版式），你只需在 JSON 抽取阶段提供准确、完整的字段值。
须覆盖全部字段键；金额精确到元；日期用 XXXX年XX月XX日；不得编造与案情冲突的内容。
"""


def _tpl(
    name: str,
    type_: str,
    description: str,
    sections: list,
    ai_prompt: str,
    title: str,
    *,
    structured: bool | None = None,
    variables: list | None = None,
) -> dict:
    use_structured = structured if structured is not None else (type_ in STRUCTURED_DOC_TYPES)
    suffix = _STRUCTURED_EXTRACTION_HINT if use_structured else _TEMPLATE_OUTPUT_RULES
    fmt = {
        **_FMT,
        "title": title,
        "word_export": "native",
        "generation_mode": "structured" if use_structured else "freeform",
    }
    return {
        "name": name,
        "type": type_,
        "description": description,
        "structure": {"sections": sections},
        "ai_prompt": ai_prompt.strip() + suffix + "\n\n案件信息：\n{context}",
        "format_rules": fmt,
        "variables": variables if variables is not None else structure_to_variables(sections),
    }


# ---------------------------------------------------------------------------
# 劳动者维权
# ---------------------------------------------------------------------------

PLATFORM_TEMPLATES: list[dict] = [
    _tpl(
        "劳动仲裁申请书",
        "application",
        "向劳动人事争议仲裁委员会申请仲裁。适用于欠薪、违法解除、未签合同、加班费、工伤待遇等。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "arbitration_commission", "label": "仲裁委员会全称", "type": "text", "required": True},
            ]},
            {"name": "申请人", "required": True, "fields": [
                {"key": "applicant_name", "label": "姓名", "type": "text", "required": True},
                {"key": "applicant_id", "label": "身份证号", "type": "text", "required": True},
                {"key": "applicant_address", "label": "住址", "type": "text", "required": True},
                {"key": "applicant_phone", "label": "联系电话", "type": "text", "required": True},
            ]},
            {"name": "被申请人", "required": True, "fields": [
                {"key": "respondent_name", "label": "用人单位名称", "type": "text", "required": True},
                {"key": "respondent_address", "label": "住所地", "type": "text", "required": True},
                {"key": "respondent_legal_rep", "label": "法定代表人", "type": "text", "required": False},
            ]},
            {"name": "仲裁请求", "required": True, "fields": [
                {"key": "requests", "label": "仲裁请求（分项列明，金额精确到元）", "type": "textarea", "required": True},
            ]},
            {"name": "事实与理由", "required": True, "fields": [
                {"key": "facts", "label": "事实经过（入职、岗位、工资、考勤、解除或欠薪）", "type": "textarea", "required": True},
                {"key": "legal_basis", "label": "法律依据", "type": "textarea", "required": True},
            ]},
            {"name": "证据", "required": True, "fields": [
                {"key": "evidence", "label": "证据目录说明", "type": "textarea", "required": True},
            ]},
            {"name": "尾部", "required": True, "fields": [
                {"key": "sign_date", "label": "申请日期", "type": "date", "required": True},
            ]},
        ],
        """从案件信息抽取劳动仲裁申请书各字段。
仲裁请求须分项列明并写清金额；事实与理由含入职、岗位、工资、解除或欠薪时间线及法律依据；证据与请求项对应；落款日期完整。""",
        "劳动仲裁申请书",
    ),
    _tpl(
        "劳动监察投诉书",
        "labor_supervision",
        "向人力资源和社会保障监察机构投诉违法用工：欠薪、未缴社保、违法加班、未签合同等。",
        [
            {"name": "投诉人", "required": True, "fields": [
                {"key": "complainant_name", "label": "投诉人", "type": "text", "required": True},
                {"key": "complainant_id", "label": "身份证号", "type": "text", "required": True},
                {"key": "complainant_phone", "label": "联系电话", "type": "text", "required": True},
            ]},
            {"name": "被投诉单位", "required": True, "fields": [
                {"key": "employer_name", "label": "用人单位", "type": "text", "required": True},
                {"key": "employer_address", "label": "单位地址", "type": "text", "required": True},
            ]},
            {"name": "投诉事项", "required": True, "fields": [
                {"key": "items", "label": "投诉事项（欠薪期间、金额、社保、加班等）", "type": "textarea", "required": True},
                {"key": "facts", "label": "事实经过", "type": "textarea", "required": True},
                {"key": "evidence", "label": "证据说明", "type": "textarea", "required": True},
                {"key": "relief", "label": "请求查处事项", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写劳动监察投诉书。列明投诉人、被投诉单位、可核查的投诉事项、时间线事实、证据及请求人社部门依法查处。""",
        "劳动监察投诉书",
    ),
    _tpl(
        "工资催告函",
        "wage_demand_letter",
        "劳动者书面催告用人单位限期支付拖欠工资（维权前置步骤之一）。",
        [
            {"name": "正文", "required": True, "fields": [
                {"key": "employer_name", "label": "致：用人单位", "type": "text", "required": True},
                {"key": "employment", "label": "入职时间、岗位、约定工资", "type": "textarea", "required": True},
                {"key": "arrears", "label": "欠薪期间与金额（元）", "type": "textarea", "required": True},
                {"key": "deadline", "label": "支付期限（X日内）", "type": "text", "required": True},
            ]},
        ],
        """请撰写工资催告函。载明劳动关系、欠薪事实与金额、限期支付要求，并保留向监察、仲裁、诉讼维权之权利。""",
        "工资催告函",
    ),
    _tpl(
        "被迫解除劳动合同通知书",
        "forced_termination_notice",
        "用人单位存在《劳动合同法》第三十八条情形时，劳动者通知解除并保留经济补偿等权利。",
        [
            {"name": "正文", "required": True, "fields": [
                {"key": "employer_name", "label": "致：用人单位", "type": "text", "required": True},
                {"key": "facts", "label": "用工事实摘要", "type": "textarea", "required": True},
                {"key": "article38_reasons", "label": "第三十八条情形（欠薪、未缴社保等）", "type": "textarea", "required": True},
                {"key": "effective_date", "label": "解除生效日期", "type": "text", "required": True},
            ]},
        ],
        """请撰写被迫解除劳动合同通知书。明确解除依据为劳动合同法第三十八条，说明解除意思及保留主张经济补偿、工资等权利。""",
        "被迫解除劳动合同通知书",
    ),
    _tpl(
        "劳动仲裁代理委托书",
        "arbitration_authorization",
        "委托律师或公民代理参加劳动仲裁。",
        [
            {"name": "委托信息", "required": True, "fields": [
                {"key": "principal", "label": "委托人（劳动者）", "type": "text", "required": True},
                {"key": "agent", "label": "受托人", "type": "text", "required": True},
                {"key": "agent_capacity", "label": "受托人身份（律师/公民代理）", "type": "text", "required": True},
                {"key": "scope", "label": "代理权限（一般/特别授权）", "type": "textarea", "required": True},
                {"key": "term", "label": "委托期限", "type": "text", "required": True},
            ]},
        ],
        """请撰写劳动仲裁代理委托书，列明委托人、受托人、代理权限范围及签章日期。""",
        "劳动仲裁代理委托书",
    ),
    _tpl(
        "劳动争议证据清单",
        "evidence_list",
        "劳动仲裁或诉讼证据目录（参考要素式起诉状证据清单栏目）。",
        [
            {"name": "基本信息", "required": True, "fields": [
                {"key": "case_ref", "label": "案号/仲裁案号", "type": "text", "required": False},
                {"key": "submitter", "label": "提交人", "type": "text", "required": True},
            ]},
            {"name": "证据列表", "required": True, "fields": [
                {"key": "items", "label": "序号、证据名称、形式、页数、证明目的", "type": "textarea", "required": True},
            ]},
        ],
        """请按序号整理证据清单：证据名称、形式（书证/电子数据等）、来源、页数、证明目的。
劳动争议常见：劳动合同、工资流水、考勤、解除通知、社保记录、聊天录音等。""",
        "证据清单",
    ),
    # ---------------------------------------------------------------------------
    # 民事（含劳动争议起诉要素式）
    # ---------------------------------------------------------------------------
    _tpl(
        "劳动争议民事起诉状",
        "complaint",
        "劳动纠纷经仲裁后不服裁决，向人民法院起诉（参考67类示范文本·劳动争议纠纷要素式结构）。",
        [
            {"name": "法院", "required": True, "fields": [
                {"key": "court_name", "label": "受理法院", "type": "text", "required": True},
            ]},
            {"name": "原告", "required": True, "fields": [
                {"key": "plaintiff_name", "label": "原告", "type": "text", "required": True},
                {"key": "plaintiff_id", "label": "身份证号", "type": "text", "required": True},
                {"key": "plaintiff_address", "label": "住所地", "type": "text", "required": True},
            ]},
            {"name": "被告", "required": True, "fields": [
                {"key": "defendant_name", "label": "被告（用人单位）", "type": "text", "required": True},
                {"key": "defendant_address", "label": "住所地", "type": "text", "required": True},
            ]},
            {"name": "仲裁前置", "required": True, "fields": [
                {"key": "arbitration_info", "label": "仲裁机构、案号、裁决摘要", "type": "textarea", "required": True},
            ]},
            {"name": "诉讼请求", "required": True, "fields": [
                {"key": "claims", "label": "诉讼请求", "type": "textarea", "required": True},
            ]},
            {"name": "事实与理由", "required": True, "fields": [
                {"key": "facts", "label": "事实与理由", "type": "textarea", "required": True},
            ]},
            {"name": "证据清单", "required": True, "fields": [
                {"key": "evidence", "label": "证据清单", "type": "textarea", "required": True},
            ]},
            {"name": "调解意愿", "required": False, "fields": [
                {"key": "mediation_willing", "label": "是否同意先行调解", "type": "text", "required": False},
            ]},
        ],
        """请撰写劳动争议民事起诉状。须载明经劳动仲裁前置程序。
结构参考要素式起诉状：当事人、仲裁情况、诉讼请求、事实与理由、证据清单、调解意愿。
适用民事诉讼法第一百二十二条；金额须明确；语言规范。""",
        "民事起诉状",
    ),
    _tpl(
        "民事答辩状",
        "answer",
        "被告针对劳动争议或其他民事起诉的答辩（要素式答辩事项+事实理由）。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "court_name", "label": "法院", "type": "text", "required": True},
                {"key": "case_number", "label": "案号", "type": "text", "required": True},
            ]},
            {"name": "答辩人", "required": True, "fields": [
                {"key": "respondent_name", "label": "答辩人", "type": "text", "required": True},
            ]},
            {"name": "答辩意见", "required": True, "fields": [
                {"key": "defense_points", "label": "对诉讼请求的逐项答辩", "type": "textarea", "required": True},
                {"key": "facts", "label": "事实与理由", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写民事答辩状。逐项回应原告诉讼请求，事实与理由条理清晰，结尾此致法院、答辩人签章与日期。""",
        "答辩状",
    ),
    _tpl(
        "民事上诉状",
        "appeal",
        "对一审民事判决、裁定不服提起上诉。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "court_name", "label": "上诉法院", "type": "text", "required": True},
                {"key": "first_instance", "label": "一审法院、案号、裁判日期", "type": "textarea", "required": True},
            ]},
            {"name": "当事人", "required": True, "fields": [
                {"key": "appellant", "label": "上诉人", "type": "text", "required": True},
                {"key": "appellee", "label": "被上诉人", "type": "text", "required": True},
            ]},
            {"name": "上诉请求", "required": True, "fields": [
                {"key": "appeal_requests", "label": "上诉请求", "type": "textarea", "required": True},
            ]},
            {"name": "上诉理由", "required": True, "fields": [
                {"key": "reasons", "label": "上诉理由（事实认定/法律适用/程序）", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写民事上诉状。列明一审信息、上诉请求、上诉理由（事实、法律、程序），引用具体条文。""",
        "上诉状",
    ),
    _tpl(
        "代理词",
        "agency_opinion",
        "庭审代理意见（民事/劳动争议）。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "agent_info", "label": "代理人及权限", "type": "text", "required": True},
            ]},
            {"name": "正文", "required": True, "fields": [
                {"key": "facts_opinion", "label": "事实认定意见", "type": "textarea", "required": True},
                {"key": "law_opinion", "label": "法律适用意见", "type": "textarea", "required": True},
                {"key": "focus", "label": "争议焦点分析", "type": "textarea", "required": True},
                {"key": "conclusion", "label": "代理意见总结", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写代理词。包括事实认定、法律适用、争议焦点、证据意见及总结请求，结语恳请法庭采纳。""",
        "代理词",
    ),
    _tpl(
        "法律意见书",
        "legal_opinion",
        "就劳动争议或民事争议出具书面法律分析意见。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "recipient", "label": "致送单位/个人", "type": "text", "required": True},
            ]},
            {"name": "正文", "required": True, "fields": [
                {"key": "background", "label": "事实背景", "type": "textarea", "required": True},
                {"key": "analysis", "label": "法律分析", "type": "textarea", "required": True},
                {"key": "opinion", "label": "结论性意见", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写法律意见书：引言、事实概述、争议焦点、法律分析、结论意见、声明与落款。""",
        "法律意见书",
    ),
    _tpl(
        "律师函",
        "lawyer_letter",
        "就欠薪、违法解除等纠纷向对方发送律师函。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "recipient", "label": "收函人", "type": "text", "required": True},
                {"key": "law_firm", "label": "律师事务所", "type": "text", "required": True},
            ]},
            {"name": "正文", "required": True, "fields": [
                {"key": "facts", "label": "事实陈述", "type": "textarea", "required": True},
                {"key": "demands", "label": "律师要求（限期履行）", "type": "textarea", "required": True},
                {"key": "consequences", "label": "法律后果告知", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写律师函。载明委托人、事实、法律依据、具体要求及不履行的法律后果，特此函告。""",
        "律师函",
    ),
    _tpl(
        "财产保全申请书",
        "preservation_application",
        "诉前或诉中财产保全申请。",
        [
            {"name": "当事人", "required": True, "fields": [
                {"key": "applicant", "label": "申请人", "type": "text", "required": True},
                {"key": "respondent", "label": "被申请人", "type": "text", "required": True},
            ]},
            {"name": "请求", "required": True, "fields": [
                {"key": "preservation_target", "label": "保全财产范围及金额", "type": "textarea", "required": True},
                {"key": "reasons", "label": "事实与理由", "type": "textarea", "required": True},
                {"key": "guarantee", "label": "担保情况", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写财产保全申请书。列明保全标的、必要性、担保，依据民事诉讼法第103条等。""",
        "财产保全申请书",
    ),
    # ---------------------------------------------------------------------------
    # 合同与调解
    # ---------------------------------------------------------------------------
    _tpl(
        "劳动合同（通用示范）",
        "labor_contract",
        "参考人社部发布的《劳动合同（通用）》示范文本，含劳动合同法第十七条必备条款。",
        [
            {"name": "合同双方", "required": True, "fields": [
                {"key": "employer_name", "label": "甲方（用人单位）", "type": "text", "required": True},
                {"key": "employer_address", "label": "甲方住所", "type": "text", "required": True},
                {"key": "employer_rep", "label": "法定代表人", "type": "text", "required": True},
                {"key": "employee_name", "label": "乙方（劳动者）", "type": "text", "required": True},
                {"key": "employee_id", "label": "乙方身份证号", "type": "text", "required": True},
                {"key": "employee_address", "label": "乙方住址", "type": "text", "required": True},
            ]},
            {"name": "一、合同期限", "required": True, "fields": [
                {"key": "term_type", "label": "期限类型（固定/无固定/以完成一定工作任务）", "type": "text", "required": True},
                {"key": "term_dates", "label": "起止日期或工作任务", "type": "text", "required": True},
                {"key": "probation", "label": "试用期约定", "type": "text", "required": False},
            ]},
            {"name": "二、工作内容与地点", "required": True, "fields": [
                {"key": "job_position", "label": "工作岗位", "type": "text", "required": True},
                {"key": "work_location", "label": "工作地点", "type": "text", "required": True},
                {"key": "job_duties", "label": "工作内容或岗位职责", "type": "textarea", "required": True},
            ]},
            {"name": "三、工作时间和休息休假", "required": True, "fields": [
                {"key": "work_hours", "label": "工时制度（标准/综合计算/不定时）", "type": "text", "required": True},
                {"key": "rest_leave", "label": "休息休假", "type": "textarea", "required": True},
            ]},
            {"name": "四、劳动报酬", "required": True, "fields": [
                {"key": "wage_standard", "label": "工资标准与支付形式", "type": "textarea", "required": True},
                {"key": "pay_date", "label": "支付日期", "type": "text", "required": True},
            ]},
            {"name": "五、社会保险和福利", "required": True, "fields": [
                {"key": "social_insurance", "label": "社会保险", "type": "textarea", "required": True},
                {"key": "benefits", "label": "福利待遇", "type": "textarea", "required": False},
            ]},
            {"name": "六、劳动保护", "required": True, "fields": [
                {"key": "labor_protection", "label": "劳动保护、劳动条件与职业危害防护", "type": "textarea", "required": True},
            ]},
            {"name": "七、其他约定", "required": False, "fields": [
                {"key": "confidentiality", "label": "保密/竞业限制等", "type": "textarea", "required": False},
                {"key": "training", "label": "培训服务期", "type": "textarea", "required": False},
                {"key": "delivery_address", "label": "送达地址与联系方式", "type": "textarea", "required": False},
            ]},
            {"name": "八、合同变更解除终止", "required": True, "fields": [
                {"key": "change_termination", "label": "变更、解除、终止条件", "type": "textarea", "required": True},
            ]},
            {"name": "九、争议解决", "required": True, "fields": [
                {"key": "dispute_resolution", "label": "争议解决方式", "type": "text", "required": True},
            ]},
            {"name": "签署", "required": True, "fields": [
                {"key": "sign_date", "label": "签订日期", "type": "date", "required": True},
            ]},
        ],
        """请根据人社部《劳动合同（通用）》示范文本精神起草劳动合同。
必须包含劳动合同法第十七条九项必备条款：用人单位与劳动者信息、合同期限、工作内容与地点、工时与休息休假、劳动报酬、社会保险、劳动保护及职业危害防护、其他法定事项。
可补充试用期、培训、保密、竞业限制、送达地址等约定；试用期须符合第十九条期限规定；工资不得低于当地最低工资。""",
        "劳动合同",
    ),
    _tpl(
        "通用民事合同",
        "contract",
        "平等主体之间设立、变更、终止民事权利义务关系的协议（买卖、服务、租赁等）。",
        [
            {"name": "当事人", "required": True, "fields": [
                {"key": "party_a", "label": "甲方", "type": "text", "required": True},
                {"key": "party_b", "label": "乙方", "type": "text", "required": True},
            ]},
            {"name": "标的与价款", "required": True, "fields": [
                {"key": "subject", "label": "合同标的", "type": "textarea", "required": True},
                {"key": "price", "label": "价款/报酬及支付", "type": "textarea", "required": True},
            ]},
            {"name": "履行", "required": True, "fields": [
                {"key": "performance", "label": "履行期限、地点与方式", "type": "textarea", "required": True},
            ]},
            {"name": "违约责任", "required": True, "fields": [
                {"key": "breach", "label": "违约责任", "type": "textarea", "required": True},
            ]},
            {"name": "争议解决", "required": True, "fields": [
                {"key": "dispute", "label": "争议解决（仲裁/诉讼）", "type": "text", "required": True},
            ]},
            {"name": "签署", "required": True, "fields": [
                {"key": "sign_date", "label": "签订日期", "type": "date", "required": True},
            ]},
        ],
        """请起草通用民事合同。结构：首部当事人、鉴于条款（如需）、标的、数量质量、价款支付、履行、验收、违约责任、不可抗力、争议解决、通知送达、附则、签署页。
条款须合法、明确、可履行；参考民法典合同编。""",
        "合同",
    ),
    _tpl(
        "劳动争议调解协议书",
        "mediation",
        "依据《劳动争议调解仲裁法》第十四条，经调解组织调解达成协议。",
        [
            {"name": "首部", "required": True, "fields": [
                {"key": "mediation_org", "label": "调解组织", "type": "text", "required": True},
                {"key": "party_worker", "label": "劳动者", "type": "text", "required": True},
                {"key": "party_employer", "label": "用人单位", "type": "text", "required": True},
            ]},
            {"name": "争议概述", "required": True, "fields": [
                {"key": "dispute_summary", "label": "争议事项与起因", "type": "textarea", "required": True},
            ]},
            {"name": "调解结果", "required": True, "fields": [
                {"key": "payment", "label": "款项金额、构成、支付方式与期限", "type": "textarea", "required": True},
                {"key": "other_obligations", "label": "其他义务（补缴社保、离职证明等）", "type": "textarea", "required": False},
            ]},
            {"name": "权利义务", "required": True, "fields": [
                {"key": "finality", "label": "纠纷终局解决与权利放弃", "type": "textarea", "required": True},
                {"key": "breach_liability", "label": "违约责任", "type": "textarea", "required": True},
            ]},
            {"name": "生效", "required": True, "fields": [
                {"key": "effective_clause", "label": "生效条件（双方签字、调解员签名、组织盖章）", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写劳动争议调解协议书。载明调解组织、当事人、争议概述、履行方案（金额须大小写）、双方终局性约定、违约责任。
注明：协议对双方有约束力；用人单位不履行时劳动者可申请仲裁；欠薪、工伤医疗费、经济补偿、赔偿金类协议可申请支付令（调解仲裁法第十六条）。""",
        "劳动争议调解协议书",
    ),
    _tpl(
        "劳动争议和解协议",
        "settlement_agreement",
        "当事人自行和解，就劳动争议一次性了结（不同于调解组织主持调解）。",
        [
            {"name": "当事人", "required": True, "fields": [
                {"key": "employer", "label": "用人单位（甲方）", "type": "text", "required": True},
                {"key": "worker", "label": "劳动者（乙方）", "type": "text", "required": True},
            ]},
            {"name": "和解内容", "required": True, "fields": [
                {"key": "settlement_amount", "label": "和解对价总额及构成", "type": "textarea", "required": True},
                {"key": "payment_terms", "label": "支付期限与账户", "type": "textarea", "required": True},
                {"key": "mutual_release", "label": "权利放弃与终局条款", "type": "textarea", "required": True},
                {"key": "breach", "label": "违约责任", "type": "textarea", "required": True},
            ]},
        ],
        """请撰写劳动争议和解协议。明确和解对价涵盖范围、付款安排、双方确认争议一次性了结及不得再就同一争议主张权利（合法范围内）。""",
        "和解协议",
    ),
]


def seed_platform_pack() -> dict:
    return seed_template_records(PLATFORM_TEMPLATES, match="type")


if __name__ == "__main__":
    print(seed_platform_pack())
