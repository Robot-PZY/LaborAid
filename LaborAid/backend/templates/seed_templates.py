"""
Seed default document templates into the database.

Usage:
    python -m templates.seed_templates

Supports both SQLite and PostgreSQL.  Honour DATABASE_URL_SYNC /
DATABASE_URL environment variables, falling back to the app config.
"""

import json
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Database connection — resolve URL from env / app config
# ---------------------------------------------------------------------------

SYNC_URL = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
if not SYNC_URL:
    try:
        from app.config import get_settings
        SYNC_URL = get_settings().DATABASE_URL_SYNC
    except Exception:
        SYNC_URL = "sqlite:///./laboraid.db"

# Strip async driver suffixes for synchronous SQLAlchemy.
SYNC_URL = SYNC_URL.replace("+aiosqlite", "").replace("+asyncpg", "")

engine = create_engine(SYNC_URL, echo=False)

# Detect dialect for SQL compatibility.
_is_sqlite = "sqlite" in SYNC_URL

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

COMMON_FORMAT_RULES = {
    "font": "仿宋",
    "size": 14,
    "line_spacing": 28,
    "margins": [37, 28, 35, 26],  # 上 右 下 左 (mm), 符合法院诉讼文书标准
    "title_font": "黑体",
    "title_size": 22,
    "subtitle_font": "楷体",
    "subtitle_size": 16,
    "paper": "A4",
}

COMMON_VARIABLES = [
    {"name": "court_name", "label": "受理法院名称", "type": "text", "required": True, "default": ""},
    {"name": "plaintiff_name", "label": "原告姓名/名称", "type": "text", "required": True, "default": ""},
    {"name": "defendant_name", "label": "被告姓名/名称", "type": "text", "required": True, "default": ""},
    {"name": "case_brief", "label": "案件简述", "type": "textarea", "required": True, "default": ""},
]

# =====================================================================
# 1. 民事起诉状 (complaint)
# =====================================================================

COMPLAINT_TEMPLATE = {
    "name": "民事起诉状",
    "type": "complaint",
    "description": "民事案件中原告向人民法院提起诉讼的正式法律文书，用于陈述诉讼请求、事实与理由。",
    "structure": {
        "sections": [
            {
                "name": "首部",
                "required": True,
                "fields": [
                    {"key": "court_name", "label": "受理法院名称", "type": "text", "required": True},
                ],
            },
            {
                "name": "原告信息",
                "required": True,
                "fields": [
                    {"key": "plaintiff_name", "label": "原告姓名/名称", "type": "text", "required": True},
                    {"key": "plaintiff_gender", "label": "性别", "type": "text", "required": False},
                    {"key": "plaintiff_birth", "label": "出生日期", "type": "date", "required": False},
                    {"key": "plaintiff_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": False},
                    {"key": "plaintiff_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "plaintiff_phone", "label": "联系电话", "type": "text", "required": False},
                    {"key": "plaintiff_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                    {"key": "plaintiff_agent", "label": "委托诉讼代理人", "type": "text", "required": False},
                ],
            },
            {
                "name": "被告信息",
                "required": True,
                "fields": [
                    {"key": "defendant_name", "label": "被告姓名/名称", "type": "text", "required": True},
                    {"key": "defendant_gender", "label": "性别", "type": "text", "required": False},
                    {"key": "defendant_birth", "label": "出生日期", "type": "date", "required": False},
                    {"key": "defendant_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": False},
                    {"key": "defendant_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "defendant_phone", "label": "联系电话", "type": "text", "required": False},
                    {"key": "defendant_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                ],
            },
            {
                "name": "第三人信息",
                "required": False,
                "fields": [
                    {"key": "third_party_name", "label": "第三人姓名/名称", "type": "text", "required": False},
                    {"key": "third_party_address", "label": "第三人住所地", "type": "text", "required": False},
                    {"key": "third_party_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": False},
                ],
            },
            {
                "name": "诉讼请求",
                "required": True,
                "fields": [
                    {"key": "claims", "label": "诉讼请求（逐条列明）", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "事实与理由",
                "required": True,
                "fields": [
                    {"key": "facts_and_reasons", "label": "事实与理由", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "证据清单",
                "required": True,
                "fields": [
                    {"key": "evidence_list", "label": "证据清单", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "submitter_name", "label": "具状人（起诉人）", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国民事诉讼律师。请根据以下信息，起草一份专业、规范、格式正确的民事起诉状。\n\n"
        "要求：\n"
        "1. 严格遵循《民事诉讼法》第一百二十一条规定的起诉状内容要求。\n"
        "2. 首部写明受理法院全称（"XX人民法院："）。\n"
        "3. 原告、被告信息完整：姓名/名称、性别、出生日期、民族、职业、住所地、联系方式。"
        "如为法人或其他组织，写明名称、住所地、法定代表人或主要负责人信息。\n"
        "4. 诉讼请求应当明确、具体、完整，逐条列明。每项请求对应具体的金额或行为要求。\n"
        "5. 事实与理由部分应当条理清晰，按时间顺序叙述事实经过，引用相关法律条文作为依据。\n"
        "6. 证据清单按照"证据名称 - 证据来源 - 证明目的"的格式逐项列明。\n"
        "7. 尾部写明"此致 XX人民法院"，具状人签名/盖章，注明日期。\n"
        "8. 语言严谨、规范，使用法律文书用语，避免口语化表述。\n"
        "9. 不得捏造事实，不得提出缺乏法律依据的诉讼请求。\n\n"
        "案件信息：\n{context}\n\n请直接生成民事起诉状正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "民事起诉状",
    },
    "variables": [
        {"name": "court_name", "label": "受理法院名称", "type": "text", "required": True, "default": ""},
        {"name": "plaintiff_name", "label": "原告姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "plaintiff_address", "label": "原告住所地", "type": "text", "required": True, "default": ""},
        {"name": "plaintiff_phone", "label": "原告联系电话", "type": "text", "required": False, "default": ""},
        {"name": "plaintiff_id_number", "label": "原告身份证号/统一社会信用代码", "type": "text", "required": False, "default": ""},
        {"name": "plaintiff_legal_rep", "label": "原告法定代表人", "type": "text", "required": False, "default": ""},
        {"name": "plaintiff_agent", "label": "原告委托诉讼代理人", "type": "text", "required": False, "default": ""},
        {"name": "defendant_name", "label": "被告姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "defendant_address", "label": "被告住所地", "type": "text", "required": True, "default": ""},
        {"name": "defendant_phone", "label": "被告联系电话", "type": "text", "required": False, "default": ""},
        {"name": "defendant_id_number", "label": "被告身份证号/统一社会信用代码", "type": "text", "required": False, "default": ""},
        {"name": "defendant_legal_rep", "label": "被告法定代表人", "type": "text", "required": False, "default": ""},
        {"name": "third_party_name", "label": "第三人姓名/名称", "type": "text", "required": False, "default": ""},
        {"name": "claims", "label": "诉讼请求", "type": "textarea", "required": True, "default": ""},
        {"name": "facts_and_reasons", "label": "事实与理由", "type": "textarea", "required": True, "default": ""},
        {"name": "evidence_list", "label": "证据清单", "type": "textarea", "required": True, "default": ""},
        {"name": "submitter_name", "label": "具状人", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 2. 答辩状 (answer)
# =====================================================================

ANSWER_TEMPLATE = {
    "name": "民事答辩状",
    "type": "answer",
    "description": "民事案件中被告针对原告起诉状提出的答辩意见，逐项回应诉讼请求并阐述答辩理由。",
    "structure": {
        "sections": [
            {
                "name": "首部",
                "required": True,
                "fields": [
                    {"key": "court_name", "label": "受理法院名称", "type": "text", "required": True},
                    {"key": "case_number", "label": "案号", "type": "text", "required": True},
                ],
            },
            {
                "name": "答辩人信息",
                "required": True,
                "fields": [
                    {"key": "respondent_name", "label": "答辩人姓名/名称", "type": "text", "required": True},
                    {"key": "respondent_gender", "label": "性别", "type": "text", "required": False},
                    {"key": "respondent_birth", "label": "出生日期", "type": "date", "required": False},
                    {"key": "respondent_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": False},
                    {"key": "respondent_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "respondent_phone", "label": "联系电话", "type": "text", "required": False},
                    {"key": "respondent_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                    {"key": "respondent_agent", "label": "委托诉讼代理人", "type": "text", "required": False},
                ],
            },
            {
                "name": "被答辩人（原告）信息",
                "required": True,
                "fields": [
                    {"key": "opposing_party_name", "label": "被答辩人姓名/名称", "type": "text", "required": True},
                    {"key": "opposing_party_address", "label": "被答辩人住所地", "type": "text", "required": False},
                ],
            },
            {
                "name": "答辩意见",
                "required": True,
                "fields": [
                    {
                        "key": "defense_opinions",
                        "label": "答辩意见（针对原告各项诉讼请求逐一答辩）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "证据",
                "required": True,
                "fields": [
                    {"key": "evidence_list", "label": "答辩证据清单", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "submitter_name", "label": "答辩人", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国民事诉讼律师。请根据以下信息，起草一份专业、规范的民事答辩状。\n\n"
        "要求：\n"
        "1. 严格遵循《民事诉讼法》相关规定及答辩状格式要求。\n"
        "2. 首部写明受理法院全称、案号。\n"
        "3. 答辩人信息完整：姓名/名称、住所地、联系方式等。\n"
        "4. 答辩意见应当针对原告起诉状中的每一项诉讼请求逐一进行答辩，逐条反驳或承认。\n"
        "   - 对于不认可的诉讼请求，阐明理由并提供相应法律依据。\n"
        "   - 对于部分认可的请求，明确认可的范围和理由。\n"
        "   - 可以提出反诉请求或程序性抗辩（如管辖权异议、诉讼时效抗辩等）。\n"
        "5. 证据部分按"证据名称 - 证据来源 - 证明目的"格式逐项列明答辩证据。\n"
        "6. 尾部写明"此致 XX人民法院"，答辩人签名/盖章，注明日期。\n"
        "7. 语言严谨、规范，法律引用准确，逻辑清晰。\n\n"
        "案件信息：\n{context}\n\n请直接生成民事答辩状正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "民事答辩状",
    },
    "variables": [
        {"name": "court_name", "label": "受理法院名称", "type": "text", "required": True, "default": ""},
        {"name": "case_number", "label": "案号", "type": "text", "required": True, "default": ""},
        {"name": "respondent_name", "label": "答辩人姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "respondent_address", "label": "答辩人住所地", "type": "text", "required": True, "default": ""},
        {"name": "respondent_phone", "label": "答辩人联系电话", "type": "text", "required": False, "default": ""},
        {"name": "respondent_id_number", "label": "答辩人身份证号/统一社会信用代码", "type": "text", "required": False, "default": ""},
        {"name": "respondent_legal_rep", "label": "答辩人法定代表人", "type": "text", "required": False, "default": ""},
        {"name": "respondent_agent", "label": "答辩人委托诉讼代理人", "type": "text", "required": False, "default": ""},
        {"name": "opposing_party_name", "label": "被答辩人（原告）姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "opposing_party_address", "label": "被答辩人住所地", "type": "text", "required": False, "default": ""},
        {"name": "defense_opinions", "label": "答辩意见", "type": "textarea", "required": True, "default": ""},
        {"name": "evidence_list", "label": "答辩证据清单", "type": "textarea", "required": True, "default": ""},
        {"name": "submitter_name", "label": "答辩人签名", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 3. 代理词 (agency_opinion)
# =====================================================================

AGENCY_OPINION_TEMPLATE = {
    "name": "代理词",
    "type": "agency_opinion",
    "description": "诉讼代理人在法庭审理终结后向法庭提交的书面代理意见，系统阐述代理观点和法律依据。",
    "structure": {
        "sections": [
            {
                "name": "开头",
                "required": True,
                "fields": [
                    {"key": "court_name", "label": "审理法院名称", "type": "text", "required": True},
                    {"key": "case_number", "label": "案号", "type": "text", "required": True},
                    {"key": "case_summary", "label": "案件概况（案由、当事人）", "type": "text", "required": True},
                    {"key": "agent_name", "label": "代理人姓名", "type": "text", "required": True},
                    {"key": "agent_role", "label": "代理身份（原告/被告代理人）", "type": "text", "required": True},
                    {"key": "client_name", "label": "被代理人姓名/名称", "type": "text", "required": True},
                ],
            },
            {
                "name": "代理意见",
                "required": True,
                "fields": [
                    {
                        "key": "agency_points",
                        "label": "代理意见（分点论述，每点含观点、事实、法律依据）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "综合意见",
                "required": True,
                "fields": [
                    {
                        "key": "summary",
                        "label": "综合意见与请求",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "结语",
                "required": True,
                "fields": [
                    {"key": "closing", "label": "结语（请求法院依法裁判）", "type": "text", "required": True},
                    {"key": "agent_signature", "label": "代理人签名", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国诉讼代理人（律师）。请根据以下信息，起草一份专业、有说服力的代理词。\n\n"
        "要求：\n"
        "1. 开头部分：写明审理法院、案号、案由及当事人基本情况，简要说明代理人出庭情况。\n"
        "2. 代理意见部分：这是代理词的核心内容，应当分点论述。\n"
        "   - 每个论点应包含：明确的主张、相关事实、法律依据、论证过程。\n"
        "   - 结合庭审中查明的事实和争议焦点进行论述。\n"
        "   - 引用具体法律条文、司法解释和相关判例。\n"
        "   - 对对方当事人不成立的主张逐一反驳。\n"
        "3. 综合意见：在分点论述的基础上进行总结归纳，明确代理人的最终请求。\n"
        "4. 结语：请求法院依法支持代理人的主张，作出公正裁判。\n"
        "5. 语言庄重、逻辑严密、论证有力，体现专业水准。\n"
        "6. 遵守《律师法》和律师执业规范，不得歪曲事实或诱导作伪证。\n\n"
        "案件信息：\n{context}\n\n请直接生成代理词正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "代理词",
    },
    "variables": [
        {"name": "court_name", "label": "审理法院名称", "type": "text", "required": True, "default": ""},
        {"name": "case_number", "label": "案号", "type": "text", "required": True, "default": ""},
        {"name": "case_summary", "label": "案件概况", "type": "text", "required": True, "default": ""},
        {"name": "agent_name", "label": "代理人姓名", "type": "text", "required": True, "default": ""},
        {"name": "agent_role", "label": "代理身份", "type": "text", "required": True, "default": ""},
        {"name": "client_name", "label": "被代理人姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "agency_points", "label": "代理意见（分点论述）", "type": "textarea", "required": True, "default": ""},
        {"name": "summary", "label": "综合意见与请求", "type": "textarea", "required": True, "default": ""},
        {"name": "closing", "label": "结语", "type": "text", "required": True, "default": "请求法院依法裁判"},
        {"name": "agent_signature", "label": "代理人签名", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 4. 辩护词 (defense_opinion)
# =====================================================================

DEFENSE_OPINION_TEMPLATE = {
    "name": "辩护词",
    "type": "defense_opinion",
    "description": "刑事案件中辩护律师向法庭提交的书面辩护意见，就指控事实、证据和法律适用提出辩护观点。",
    "structure": {
        "sections": [
            {
                "name": "开头",
                "required": True,
                "fields": [
                    {"key": "court_name", "label": "审理法院名称", "type": "text", "required": True},
                    {"key": "case_number", "label": "案号", "type": "text", "required": True},
                    {"key": "defendant_name", "label": "被告人姓名", "type": "text", "required": True},
                    {"key": "charges", "label": "指控罪名", "type": "text", "required": True},
                    {"key": "defender_name", "label": "辩护人姓名", "type": "text", "required": True},
                    {"key": "defender_firm", "label": "辩护人所在律所", "type": "text", "required": True},
                ],
            },
            {
                "name": "辩护意见",
                "required": True,
                "fields": [
                    {
                        "key": "defense_points",
                        "label": "辩护意见（分点论述：事实、证据、法律适用）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "量刑意见",
                "required": True,
                "fields": [
                    {
                        "key": "sentencing_opinion",
                        "label": "量刑辩护意见（从轻、减轻或免除处罚的理由）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "结语",
                "required": True,
                "fields": [
                    {"key": "closing", "label": "结语与请求", "type": "textarea", "required": True},
                    {"key": "defender_signature", "label": "辩护人签名", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国刑事辩护律师。请根据以下信息，起草一份专业、有力的刑事辩护词。\n\n"
        "要求：\n"
        "1. 开头部分：写明审理法院、案号、被告人姓名、被指控罪名，以及辩护人的身份信息。\n"
        "2. 辩护意见部分：这是辩护词的核心，应从以下角度逐一论述：\n"
        "   a) 事实方面：指控事实是否清楚，是否存在事实不清、证据不足的情形。\n"
        "   b) 证据方面：审查证据的合法性、真实性和关联性，指出证据链的缺陷。\n"
        "   c) 法律适用方面：指控罪名是否成立，是否应定性为其他较轻罪名。\n"
        "   d) 程序方面：是否存在违反法定程序的情形。\n"
        "3. 量刑意见：如有从轻、减轻或免除处罚的情节，逐项列明：\n"
        "   - 自首、坦白、立功\n"
        "   - 初犯、偶犯\n"
        "   - 赔偿损失、取得谅解\n"
        "   - 主从犯区分\n"
        "   - 犯罪未遂、中止\n"
        "   - 未成年、年满七十五周岁等法定从宽情节\n"
        "4. 结语：概括辩护观点，明确请求法院作出无罪或罪轻判决。\n"
        "5. 语言庄重、论证有力、法律依据充分，严格遵守《刑事诉讼法》和律师执业规范。\n"
        "6. 不得教唆伪造证据或作虚假陈述。\n\n"
        "案件信息：\n{context}\n\n请直接生成辩护词正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "辩护词",
    },
    "variables": [
        {"name": "court_name", "label": "审理法院名称", "type": "text", "required": True, "default": ""},
        {"name": "case_number", "label": "案号", "type": "text", "required": True, "default": ""},
        {"name": "defendant_name", "label": "被告人姓名", "type": "text", "required": True, "default": ""},
        {"name": "charges", "label": "指控罪名", "type": "text", "required": True, "default": ""},
        {"name": "defender_name", "label": "辩护人姓名", "type": "text", "required": True, "default": ""},
        {"name": "defender_firm", "label": "辩护人所在律所", "type": "text", "required": True, "default": ""},
        {"name": "defense_points", "label": "辩护意见（分点论述）", "type": "textarea", "required": True, "default": ""},
        {"name": "sentencing_opinion", "label": "量刑辩护意见", "type": "textarea", "required": True, "default": ""},
        {"name": "closing", "label": "结语与请求", "type": "textarea", "required": True, "default": ""},
        {"name": "defender_signature", "label": "辩护人签名", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 5. 法律意见书 (legal_opinion)
# =====================================================================

LEGAL_OPINION_TEMPLATE = {
    "name": "法律意见书",
    "type": "legal_opinion",
    "description": "律师接受委托后，就特定法律事务进行调查分析，向委托人出具的书面法律意见和专业建议。",
    "structure": {
        "sections": [
            {
                "name": "基本信息",
                "required": True,
                "fields": [
                    {"key": "opinion_title", "label": "法律意见书标题", "type": "text", "required": True},
                    {"key": "client_name", "label": "委托人姓名/名称", "type": "text", "required": True},
                    {"key": "lawyer_name", "label": "出具律师姓名", "type": "text", "required": True},
                    {"key": "law_firm", "label": "律师事务所名称", "type": "text", "required": True},
                    {"key": "issue_date", "label": "出具日期", "type": "date", "required": True},
                ],
            },
            {
                "name": "委托事项",
                "required": True,
                "fields": [
                    {"key": "entrustment_matter", "label": "委托事项及背景", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "事实概述",
                "required": True,
                "fields": [
                    {"key": "facts_summary", "label": "事实概述", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "法律分析",
                "required": True,
                "fields": [
                    {"key": "legal_analysis", "label": "法律分析", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "结论建议",
                "required": True,
                "fields": [
                    {"key": "conclusions", "label": "结论与建议", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "声明",
                "required": True,
                "fields": [
                    {"key": "disclaimer", "label": "声明与免责条款", "type": "textarea", "required": False},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国律师。请根据以下信息，起草一份专业、全面的法律意见书。\n\n"
        "要求：\n"
        "1. 标题写明"关于XXX的法律意见书"。\n"
        "2. 委托事项部分：明确写明委托人、委托事项、委托背景。\n"
        "3. 事实概述部分：客观、准确地归纳与委托事项相关的事实情况，注明事实来源。\n"
        "4. 法律分析部分：这是核心内容，要求：\n"
        "   - 系统梳理相关法律法规、司法解释、部门规章。\n"
        "   - 分析委托事项的法律性质和法律关系。\n"
        "   - 对可能存在的法律风险进行评估。\n"
        "   - 引用具体法律条文并注明出处。\n"
        "   - 如存在多种法律观点，应分别阐述并给出倾向性意见。\n"
        "5. 结论与建议部分：\n"
        "   - 明确给出法律结论。\n"
        "   - 提出可操作的建议方案。\n"
        "   - 如存在风险，给出风险防范措施。\n"
        "6. 声明部分：注明意见书的使用范围限制、免责声明。\n"
        "7. 引用的法律须注明具体条文，确保法律依据准确、有效。\n\n"
        "委托事项信息：\n{context}\n\n请直接生成法律意见书正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "法律意见书",
    },
    "variables": [
        {"name": "opinion_title", "label": "法律意见书标题", "type": "text", "required": True, "default": ""},
        {"name": "client_name", "label": "委托人姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "lawyer_name", "label": "出具律师姓名", "type": "text", "required": True, "default": ""},
        {"name": "law_firm", "label": "律师事务所名称", "type": "text", "required": True, "default": ""},
        {"name": "issue_date", "label": "出具日期", "type": "date", "required": True, "default": ""},
        {"name": "entrustment_matter", "label": "委托事项及背景", "type": "textarea", "required": True, "default": ""},
        {"name": "facts_summary", "label": "事实概述", "type": "textarea", "required": True, "default": ""},
        {"name": "legal_analysis", "label": "法律分析", "type": "textarea", "required": True, "default": ""},
        {"name": "conclusions", "label": "结论与建议", "type": "textarea", "required": True, "default": ""},
        {"name": "disclaimer", "label": "声明与免责条款", "type": "textarea", "required": False, "default": ""},
    ],
}

# =====================================================================
# 6. 律师函 (lawyer_letter)
# =====================================================================

LAWYER_LETTER_TEMPLATE = {
    "name": "律师函",
    "type": "lawyer_letter",
    "description": "律师接受委托人委托，向相关方发送的正式法律函件，用于主张权利、催告履行或提出法律警告。",
    "structure": {
        "sections": [
            {
                "name": "函件基本信息",
                "required": True,
                "fields": [
                    {"key": "letter_title", "label": "函件标题", "type": "text", "required": True},
                    {"key": "recipient_name", "label": "致函对象（收函人）姓名/名称", "type": "text", "required": True},
                    {"key": "recipient_address", "label": "收函人地址", "type": "text", "required": True},
                ],
            },
            {
                "name": "致函对象",
                "required": True,
                "fields": [
                    {"key": "recipient_salutation", "label": "致函称呼", "type": "text", "required": True},
                ],
            },
            {
                "name": "事实陈述",
                "required": True,
                "fields": [
                    {"key": "facts_statement", "label": "事实陈述", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "法律依据",
                "required": True,
                "fields": [
                    {"key": "legal_basis", "label": "法律依据", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "要求事项",
                "required": True,
                "fields": [
                    {"key": "demands", "label": "要求事项", "type": "textarea", "required": True},
                    {"key": "deadline", "label": "履行期限", "type": "text", "required": True},
                ],
            },
            {
                "name": "后果告知",
                "required": True,
                "fields": [
                    {"key": "consequences", "label": "不履行后果告知", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "lawyer_name", "label": "发函律师姓名", "type": "text", "required": True},
                    {"key": "law_firm", "label": "律师事务所名称", "type": "text", "required": True},
                    {"key": "lawyer_phone", "label": "律师联系电话", "type": "text", "required": False},
                    {"key": "issue_date", "label": "发函日期", "type": "date", "required": True},
                    {"key": "client_name", "label": "委托人", "type": "text", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国律师。请根据以下信息，起草一份正式、严谨的律师函。\n\n"
        "要求：\n"
        "1. 标题格式："XX律师事务所关于XXX的律师函"。\n"
        "2. 致函对象部分：写明收函人的完整名称和地址，以及"致XX"的称呼。\n"
        "3. 事实陈述部分：客观、准确地陈述与委托事项相关的事实，注明时间、地点、涉及金额等关键要素。\n"
        "4. 法律依据部分：\n"
        "   - 引用与本案相关的法律法规具体条文。\n"
        "   - 说明收函人行为的法律性质。\n"
        "   - 指出其行为已构成违约或侵权。\n"
        "5. 要求事项部分：\n"
        "   - 明确、具体地提出委托人的要求。\n"
        "   - 设定合理的履行期限。\n"
        "   - 告知履行方式（如付款账户信息等）。\n"
        "6. 后果告知部分：\n"
        "   - 告知如不在期限内履行，委托人将采取的法律措施（如诉讼、仲裁、举报等）。\n"
        "   - 提醒由此产生的额外费用（诉讼费、律师费等）将由对方承担。\n"
        "7. 尾部：注明发函律师、律师事务所、联系方式、发函日期。\n"
        "8. 语气坚定但不过激，措辞专业且具有法律威慑力。\n\n"
        "委托事项信息：\n{context}\n\n请直接生成律师函正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "律师函",
        "letterhead_font": "黑体",
        "letterhead_size": 18,
    },
    "variables": [
        {"name": "letter_title", "label": "函件标题", "type": "text", "required": True, "default": ""},
        {"name": "recipient_name", "label": "致函对象姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "recipient_address", "label": "收函人地址", "type": "text", "required": True, "default": ""},
        {"name": "recipient_salutation", "label": "致函称呼", "type": "text", "required": True, "default": ""},
        {"name": "facts_statement", "label": "事实陈述", "type": "textarea", "required": True, "default": ""},
        {"name": "legal_basis", "label": "法律依据", "type": "textarea", "required": True, "default": ""},
        {"name": "demands", "label": "要求事项", "type": "textarea", "required": True, "default": ""},
        {"name": "deadline", "label": "履行期限", "type": "text", "required": True, "default": ""},
        {"name": "consequences", "label": "不履行后果告知", "type": "textarea", "required": True, "default": ""},
        {"name": "lawyer_name", "label": "发函律师姓名", "type": "text", "required": True, "default": ""},
        {"name": "law_firm", "label": "律师事务所名称", "type": "text", "required": True, "default": ""},
        {"name": "lawyer_phone", "label": "律师联系电话", "type": "text", "required": False, "default": ""},
        {"name": "issue_date", "label": "发函日期", "type": "date", "required": True, "default": ""},
        {"name": "client_name", "label": "委托人", "type": "text", "required": True, "default": ""},
    ],
}

# =====================================================================
# 7. 证据清单 (evidence_list)
# =====================================================================

EVIDENCE_LIST_TEMPLATE = {
    "name": "证据清单",
    "type": "evidence_list",
    "description": "劳动仲裁或诉讼中提交的证据目录，列明工资条、聊天记录、考勤等材料及证明目的。",
    "structure": {
        "sections": [
            {
                "name": "基本信息",
                "required": True,
                "fields": [
                    {"key": "case_number", "label": "案号", "type": "text", "required": True},
                    {"key": "party_name", "label": "提交方（当事人姓名/名称）", "type": "text", "required": True},
                    {"key": "party_role", "label": "诉讼地位（原告/被告/第三人）", "type": "text", "required": True},
                    {"key": "court_name", "label": "受理法院", "type": "text", "required": True},
                ],
            },
            {
                "name": "证据列表",
                "required": True,
                "fields": [
                    {
                        "key": "evidence_items",
                        "label": "证据列表（含序号、证据名称、证据类型、页数、证明目的）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "submitter_name", "label": "提交人", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国诉讼律师。请根据以下信息，整理一份规范、完整的证据清单。\n\n"
        "要求：\n"
        "1. 按照法院标准的证据清单格式制作。\n"
        "2. 每项证据按以下格式列明：\n"
        "   序号 | 证据名称 | 证据类型 | 证据来源 | 页数 | 证明目的\n"
        "3. 证据类型包括但不限于：书证、物证、视听资料、电子数据、证人证言、鉴定意见、勘验笔录。\n"
        "4. 证明目的应当明确、具体，与案件争议焦点紧密相关。\n"
        "5. 证据编排应有逻辑性，按照：\n"
        "   a) 主体资格证据（身份证明、营业执照等）\n"
        "   b) 实体权利证据（合同、协议、转账记录等）\n"
        "   c) 程序性证据（送达回证、通知等）\n"
        "   d) 损失证据（评估报告、票据等）\n"
        "6. 注明原件/复印件。\n\n"
        "案件信息：\n{context}\n\n请直接生成证据清单内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "证据清单",
        "table_header_font": "黑体",
        "table_header_size": 12,
        "table_border": True,
    },
    "variables": [
        {"name": "case_number", "label": "案号", "type": "text", "required": True, "default": ""},
        {"name": "party_name", "label": "提交方姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "party_role", "label": "诉讼地位", "type": "text", "required": True, "default": ""},
        {"name": "court_name", "label": "受理法院", "type": "text", "required": True, "default": ""},
        {"name": "evidence_items", "label": "证据列表", "type": "textarea", "required": True, "default": ""},
        {"name": "submitter_name", "label": "提交人", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 8. 质证意见 (cross_examination)
# =====================================================================

CROSS_EXAMINATION_TEMPLATE = {
    "name": "质证意见",
    "type": "cross_examination",
    "description": "诉讼当事人对对方提交的证据进行质证，从真实性、合法性、关联性三方面发表意见。",
    "structure": {
        "sections": [
            {
                "name": "基本信息",
                "required": True,
                "fields": [
                    {"key": "case_number", "label": "案号", "type": "text", "required": True},
                    {"key": "court_name", "label": "审理法院", "type": "text", "required": True},
                    {"key": "examiner_name", "label": "质证方（当事人）姓名/名称", "type": "text", "required": True},
                    {"key": "examiner_role", "label": "质证方诉讼地位", "type": "text", "required": True},
                    {"key": "evidence_provider", "label": "举证方（对方当事人）姓名/名称", "type": "text", "required": True},
                ],
            },
            {
                "name": "质证意见",
                "required": True,
                "fields": [
                    {
                        "key": "cross_exam_items",
                        "label": "逐项质证意见（含对方证据名称、真实性、合法性、关联性意见）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "综合意见",
                "required": False,
                "fields": [
                    {
                        "key": "overall_opinion",
                        "label": "对对方整体证据体系的综合质证意见",
                        "type": "textarea",
                        "required": False,
                    },
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "submitter_name", "label": "质证人签名", "type": "text", "required": True},
                    {"key": "submission_date", "label": "提交日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国诉讼律师。请根据以下信息，起草一份专业、全面的质证意见。\n\n"
        "要求：\n"
        "1. 逐一对对方提交的每项证据发表质证意见。\n"
        "2. 每项证据从以下三个维度进行质证：\n"
        "   a) 真实性：证据是否真实、是否存在伪造或篡改的可能。\n"
        "   b) 合法性：证据的收集程序、形式是否符合法律规定。\n"
        "   c) 关联性：证据与案件争议焦点是否具有关联，能否证明待证事实。\n"
        "3. 质证意见格式：\n"
        "   证据序号 + 证据名称\n"
        "   - 对真实性：认可/不认可 + 理由\n"
        "   - 对合法性：认可/不认可 + 理由\n"
        "   - 对关联性：认可/不认可 + 理由\n"
        "   - 综合意见：是否同意作为定案依据\n"
        "4. 综合质证意见：对对方整体证据体系的完整性、证明力进行评价。\n"
        "5. 如对方证据存在疑点，应明确指出并说明理由。\n"
        "6. 引用相关法律条文和司法解释支持质证观点。\n\n"
        "案件信息：\n{context}\n\n请直接生成质证意见正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "质证意见",
    },
    "variables": [
        {"name": "case_number", "label": "案号", "type": "text", "required": True, "default": ""},
        {"name": "court_name", "label": "审理法院", "type": "text", "required": True, "default": ""},
        {"name": "examiner_name", "label": "质证方姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "examiner_role", "label": "质证方诉讼地位", "type": "text", "required": True, "default": ""},
        {"name": "evidence_provider", "label": "举证方姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "cross_exam_items", "label": "逐项质证意见", "type": "textarea", "required": True, "default": ""},
        {"name": "overall_opinion", "label": "综合质证意见", "type": "textarea", "required": False, "default": ""},
        {"name": "submitter_name", "label": "质证人签名", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "提交日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 9. 财产保全申请书 (preservation_application)
# =====================================================================

PRESERVATION_APPLICATION_TEMPLATE = {
    "name": "财产保全申请书",
    "type": "preservation_application",
    "description": "诉讼前或诉讼中，为防止对方转移、隐匿财产，向法院申请对对方财产采取保全措施的法律文书。",
    "structure": {
        "sections": [
            {
                "name": "首部",
                "required": True,
                "fields": [
                    {"key": "court_name", "label": "受理法院名称", "type": "text", "required": True},
                    {"key": "case_number", "label": "案号（诉中保全填写，诉前保全不填）", "type": "text", "required": False},
                ],
            },
            {
                "name": "申请人信息",
                "required": True,
                "fields": [
                    {"key": "applicant_name", "label": "申请人姓名/名称", "type": "text", "required": True},
                    {"key": "applicant_gender", "label": "性别", "type": "text", "required": False},
                    {"key": "applicant_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": True},
                    {"key": "applicant_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "applicant_phone", "label": "联系电话", "type": "text", "required": True},
                    {"key": "applicant_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                ],
            },
            {
                "name": "被申请人信息",
                "required": True,
                "fields": [
                    {"key": "respondent_name", "label": "被申请人姓名/名称", "type": "text", "required": True},
                    {"key": "respondent_id_number", "label": "身份证号/统一社会信用代码", "type": "text", "required": True},
                    {"key": "respondent_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "respondent_phone", "label": "联系电话", "type": "text", "required": False},
                    {"key": "respondent_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                ],
            },
            {
                "name": "请求事项",
                "required": True,
                "fields": [
                    {
                        "key": "preservation_requests",
                        "label": "保全请求（保全财产范围、金额、方式）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "事实与理由",
                "required": True,
                "fields": [
                    {
                        "key": "facts_and_reasons",
                        "label": "申请保全的事实与理由（含紧急情况说明）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "担保",
                "required": True,
                "fields": [
                    {
                        "key": "guarantee_info",
                        "label": "担保情况（担保方式、担保财产）",
                        "type": "textarea",
                        "required": True,
                    },
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "submitter_name", "label": "申请人签名", "type": "text", "required": True},
                    {"key": "submission_date", "label": "申请日期", "type": "date", "required": True},
                ],
            },
        ]
    },
    "ai_prompt": (
        "你是一名资深中国民事诉讼律师。请根据以下信息，起草一份规范、完整的财产保全申请书。\n\n"
        "要求：\n"
        "1. 严格遵循《民事诉讼法》第一百零三条（诉中保全）和第一百零四条（诉前保全）的规定。\n"
        "2. 首部写明受理法院全称。\n"
        "3. 申请人、被申请人信息完整：姓名/名称、住所地、联系方式等。\n"
        "4. 请求事项部分：\n"
        "   - 明确请求保全的财产范围和具体金额。\n"
        "   - 列明需要查封、扣押、冻结的具体财产（银行账户、房产、车辆等）。\n"
        "   - 写明保全的金额上限。\n"
        "5. 事实与理由部分：\n"
        "   - 阐述申请人与被申请人之间的债权债务关系或争议。\n"
        "   - 说明存在紧急情况，如不保全将使判决难以执行或造成其他损害。\n"
        "   - 列明被申请人可能转移、隐匿财产的具体情形。\n"
        "6. 担保部分：写明申请人提供的担保方式和担保财产。\n"
        "7. 尾部：写明"此致 XX人民法院"，申请人签名，注明日期。\n"
        "8. 语言严谨、事实清楚、理由充分。\n\n"
        "案件信息：\n{context}\n\n请直接生成财产保全申请书正文内容。"
    ),
    "format_rules": {
        **COMMON_FORMAT_RULES,
        "title": "财产保全申请书",
    },
    "variables": [
        {"name": "court_name", "label": "受理法院名称", "type": "text", "required": True, "default": ""},
        {"name": "case_number", "label": "案号（诉中保全）", "type": "text", "required": False, "default": ""},
        {"name": "applicant_name", "label": "申请人姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "applicant_id_number", "label": "申请人身份证号/统一社会信用代码", "type": "text", "required": True, "default": ""},
        {"name": "applicant_address", "label": "申请人住所地", "type": "text", "required": True, "default": ""},
        {"name": "applicant_phone", "label": "申请人联系电话", "type": "text", "required": True, "default": ""},
        {"name": "applicant_legal_rep", "label": "申请人法定代表人", "type": "text", "required": False, "default": ""},
        {"name": "respondent_name", "label": "被申请人姓名/名称", "type": "text", "required": True, "default": ""},
        {"name": "respondent_id_number", "label": "被申请人身份证号/统一社会信用代码", "type": "text", "required": True, "default": ""},
        {"name": "respondent_address", "label": "被申请人住所地", "type": "text", "required": True, "default": ""},
        {"name": "respondent_phone", "label": "被申请人联系电话", "type": "text", "required": False, "default": ""},
        {"name": "respondent_legal_rep", "label": "被申请人法定代表人", "type": "text", "required": False, "default": ""},
        {"name": "preservation_requests", "label": "保全请求", "type": "textarea", "required": True, "default": ""},
        {"name": "facts_and_reasons", "label": "事实与理由", "type": "textarea", "required": True, "default": ""},
        {"name": "guarantee_info", "label": "担保情况", "type": "textarea", "required": True, "default": ""},
        {"name": "submitter_name", "label": "申请人签名", "type": "text", "required": True, "default": ""},
        {"name": "submission_date", "label": "申请日期", "type": "date", "required": True, "default": ""},
    ],
}

# =====================================================================
# 劳动者平台 — 劳动仲裁申请书 (application)
# =====================================================================

LABOR_ARBITRATION_APPLICATION_TEMPLATE = {
    "name": "劳动仲裁申请书",
    "type": "application",
    "description": "劳动者向劳动人事争议仲裁委员会申请仲裁时使用，适用于欠薪、违法解除、未签劳动合同、加班费、工伤待遇等争议。",
    "structure": {
        "sections": [
            {
                "name": "首部",
                "required": True,
                "fields": [
                    {"key": "arbitration_commission", "label": "仲裁委员会名称", "type": "text", "required": True},
                ],
            },
            {
                "name": "申请人（劳动者）信息",
                "required": True,
                "fields": [
                    {"key": "applicant_name", "label": "姓名", "type": "text", "required": True},
                    {"key": "applicant_gender", "label": "性别", "type": "text", "required": False},
                    {"key": "applicant_id_number", "label": "身份证号", "type": "text", "required": True},
                    {"key": "applicant_phone", "label": "联系电话", "type": "text", "required": True},
                    {"key": "applicant_address", "label": "住址/送达地址", "type": "text", "required": True},
                ],
            },
            {
                "name": "被申请人（用人单位）信息",
                "required": True,
                "fields": [
                    {"key": "respondent_name", "label": "单位名称", "type": "text", "required": True},
                    {"key": "respondent_address", "label": "住所地", "type": "text", "required": True},
                    {"key": "respondent_legal_rep", "label": "法定代表人", "type": "text", "required": False},
                    {"key": "respondent_credit_code", "label": "统一社会信用代码", "type": "text", "required": False},
                ],
            },
            {
                "name": "仲裁请求",
                "required": True,
                "fields": [
                    {"key": "arbitration_requests", "label": "仲裁请求（分项列明）", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "事实与理由",
                "required": True,
                "fields": [
                    {"key": "employment_facts", "label": "入职、岗位、工资、解除等事实", "type": "textarea", "required": True},
                    {"key": "legal_reasons", "label": "法律依据与理由", "type": "textarea", "required": True},
                ],
            },
            {
                "name": "尾部",
                "required": True,
                "fields": [
                    {"key": "evidence_note", "label": "证据材料说明", "type": "textarea", "required": False},
                    {"key": "submitter_name", "label": "申请人签名", "type": "text", "required": True},
                    {"key": "submission_date", "label": "申请日期", "type": "date", "required": True},
                ],
            },
        ],
    },
    "ai_prompt": (
        "你是一名熟悉劳动争议仲裁实务的法律文书助手，请根据以下案件信息生成《劳动仲裁申请书》。\n\n"
        "要求：\n"
        "1. 标题为「劳动仲裁申请书」。\n"
        "2. 首部写明「致：XX劳动人事争议仲裁委员会」。\n"
        "3. 列明申请人（劳动者）与被申请人（用人单位）基本信息。\n"
        "4. 仲裁请求须具体可执行：补发工资、经济补偿/赔偿金、确认劳动关系、未签合同二倍工资、加班费等分项编号。\n"
        "5. 事实与理由按时间线写清入职、岗位、工资标准、考勤/加班、解除或欠薪经过，并引用《劳动争议调解仲裁法》《劳动合同法》等条文。\n"
        "6. 注明附件证据清单（如劳动合同、工资流水、聊天记录、解除通知等）。\n"
        "7. 结尾「此致 XX劳动人事争议仲裁委员会」，申请人签名及日期。\n"
        "8. 语言朴实准确，便于劳动者本人提交。\n\n"
        "案件信息：\n{context}\n\n请直接输出申请书正文。"
    ),
    "format_rules": {**COMMON_FORMAT_RULES, "title": "劳动仲裁申请书"},
    "variables": [
        {"name": "arbitration_commission", "label": "仲裁委员会名称", "type": "text", "required": True, "default": ""},
        {"name": "applicant_name", "label": "申请人姓名", "type": "text", "required": True, "default": ""},
        {"name": "respondent_name", "label": "用人单位名称", "type": "text", "required": True, "default": ""},
        {"name": "arbitration_requests", "label": "仲裁请求", "type": "textarea", "required": True, "default": ""},
        {"name": "employment_facts", "label": "事实经过", "type": "textarea", "required": True, "default": ""},
    ],
}

# =====================================================================
# 劳动者平台 — 劳动监察投诉书 (labor_supervision)
# =====================================================================

LABOR_SUPERVISION_COMPLAINT_TEMPLATE = {
    "name": "劳动监察投诉书",
    "type": "labor_supervision",
    "description": "向人力资源和社会保障监察机构投诉用人单位违法用工（欠薪、未缴社保、违法加班等）。",
    "structure": {
        "sections": [
            {
                "name": "投诉人信息",
                "required": True,
                "fields": [
                    {"key": "complainant_name", "label": "投诉人姓名", "type": "text", "required": True},
                    {"key": "complainant_id_number", "label": "身份证号", "type": "text", "required": True},
                    {"key": "complainant_phone", "label": "联系电话", "type": "text", "required": True},
                ],
            },
            {
                "name": "被投诉单位",
                "required": True,
                "fields": [
                    {"key": "employer_name", "label": "用人单位名称", "type": "text", "required": True},
                    {"key": "employer_address", "label": "单位地址", "type": "text", "required": True},
                ],
            },
            {
                "name": "投诉事项",
                "required": True,
                "fields": [
                    {"key": "complaint_items", "label": "投诉请求（欠薪金额、社保、加班等）", "type": "textarea", "required": True},
                    {"key": "facts", "label": "事实经过", "type": "textarea", "required": True},
                ],
            },
        ],
    },
    "ai_prompt": (
        "请根据案件信息撰写《劳动监察投诉书》，供劳动者向人社监察部门提交。\n\n"
        "须包含：投诉人信息、被投诉用人单位、投诉事项（欠薪、未缴社保、违法解除、超时加班等）、"
        "事实经过、证据说明、请求监察机关依法查处。语言简洁，突出可核查事实与金额。\n\n"
        "案件信息：\n{context}\n\n请直接输出投诉书正文。"
    ),
    "format_rules": {**COMMON_FORMAT_RULES, "title": "劳动监察投诉书"},
    "variables": [
        {"name": "complainant_name", "label": "投诉人", "type": "text", "required": True, "default": ""},
        {"name": "employer_name", "label": "用人单位", "type": "text", "required": True, "default": ""},
        {"name": "complaint_items", "label": "投诉事项", "type": "textarea", "required": True, "default": ""},
    ],
}

# =====================================================================
# 劳动者 — 工资催告函 (wage_demand_letter)
# =====================================================================

WAGE_DEMAND_LETTER_TEMPLATE = {
    "name": "工资催告函",
    "type": "wage_demand_letter",
    "description": "劳动者向用人单位发送书面催告，要求限期支付拖欠工资，可作为维权前置材料。",
    "structure": {
        "sections": [
            {
                "name": "函件信息",
                "required": True,
                "fields": [
                    {"key": "employer_name", "label": "用人单位名称", "type": "text", "required": True},
                    {"key": "employee_name", "label": "劳动者姓名", "type": "text", "required": True},
                ],
            },
            {
                "name": "正文",
                "required": True,
                "fields": [
                    {"key": "wage_period", "label": "欠薪期间", "type": "text", "required": True},
                    {"key": "wage_amount", "label": "欠付金额", "type": "text", "required": True},
                    {"key": "facts", "label": "事实陈述", "type": "textarea", "required": True},
                    {"key": "deadline", "label": "支付期限", "type": "text", "required": True},
                ],
            },
        ],
    },
    "ai_prompt": (
        "请撰写《工资催告函》，语气正式、克制，列明欠薪期间、金额、支付期限及逾期后果。"
        "案件信息：\n{context}\n\n请直接输出正文。"
    ),
    "format_rules": {**COMMON_FORMAT_RULES, "title": "工资催告函"},
    "variables": [
        {"name": "employer_name", "label": "用人单位", "type": "text", "required": True, "default": ""},
        {"name": "employee_name", "label": "劳动者", "type": "text", "required": True, "default": ""},
        {"name": "wage_amount", "label": "欠付金额", "type": "text", "required": True, "default": ""},
    ],
}

# =====================================================================
# 劳动者 — 被迫解除劳动合同通知书 (forced_termination_notice)
# =====================================================================

FORCED_TERMINATION_NOTICE_TEMPLATE = {
    "name": "被迫解除劳动合同通知书",
    "type": "forced_termination_notice",
    "description": "用人单位存在劳动合同法第三十八条情形时，劳动者可书面通知解除合同并主张经济补偿。",
    "structure": {
        "sections": [
            {
                "name": "通知信息",
                "required": True,
                "fields": [
                    {"key": "employer_name", "label": "用人单位名称", "type": "text", "required": True},
                    {"key": "employee_name", "label": "劳动者姓名", "type": "text", "required": True},
                    {"key": "termination_date", "label": "解除日期", "type": "date", "required": True},
                ],
            },
            {
                "name": "解除理由",
                "required": True,
                "fields": [
                    {"key": "reasons", "label": "被迫解除的具体事由（未足额支付报酬、未缴社保等）", "type": "textarea", "required": True},
                    {"key": "legal_basis", "label": "法律依据", "type": "textarea", "required": True},
                    {"key": "requests", "label": "后续请求（办理离职、支付经济补偿等）", "type": "textarea", "required": True},
                ],
            },
        ],
    },
    "ai_prompt": (
        "请撰写《被迫解除劳动合同通知书》，引用劳动合同法第三十八条、第四十六条等，"
        "列明解除事由、解除日期及请求事项。案件信息：\n{context}\n\n请直接输出正文。"
    ),
    "format_rules": {**COMMON_FORMAT_RULES, "title": "被迫解除劳动合同通知书"},
    "variables": [
        {"name": "employer_name", "label": "用人单位", "type": "text", "required": True, "default": ""},
        {"name": "employee_name", "label": "劳动者", "type": "text", "required": True, "default": ""},
    ],
}

# =====================================================================
# 劳动者 — 劳动仲裁代理委托书 (arbitration_authorization)
# =====================================================================

ARBITRATION_AUTHORIZATION_TEMPLATE = {
    "name": "劳动仲裁代理委托书",
    "type": "arbitration_authorization",
    "description": "劳动者委托律师或公民代理参加劳动仲裁的授权文书。",
    "structure": {
        "sections": [
            {
                "name": "委托信息",
                "required": True,
                "fields": [
                    {"key": "principal_name", "label": "委托人（劳动者）", "type": "text", "required": True},
                    {"key": "agent_name", "label": "受托人", "type": "text", "required": True},
                    {"key": "agent_relation", "label": "与委托人关系/执业机构", "type": "text", "required": True},
                    {"key": "commission_name", "label": "仲裁委员会", "type": "text", "required": True},
                    {"key": "case_summary", "label": "案件简述", "type": "textarea", "required": True},
                    {"key": "authority_scope", "label": "代理权限（一般/特别授权）", "type": "text", "required": True},
                ],
            },
        ],
    },
    "ai_prompt": (
        "请撰写《劳动仲裁代理委托书》，列明委托人、受托人、案件、代理权限及期限。"
        "案件信息：\n{context}\n\n请直接输出正文。"
    ),
    "format_rules": {**COMMON_FORMAT_RULES, "title": "劳动仲裁代理委托书"},
    "variables": [
        {"name": "principal_name", "label": "委托人", "type": "text", "required": True, "default": ""},
        {"name": "agent_name", "label": "受托人", "type": "text", "required": True, "default": ""},
    ],
}

# ---------------------------------------------------------------------------
# All templates assembled
# ---------------------------------------------------------------------------

ALL_TEMPLATES = [
    COMPLAINT_TEMPLATE,
    ANSWER_TEMPLATE,
    AGENCY_OPINION_TEMPLATE,
    DEFENSE_OPINION_TEMPLATE,
    LEGAL_OPINION_TEMPLATE,
    LAWYER_LETTER_TEMPLATE,
    EVIDENCE_LIST_TEMPLATE,
    CROSS_EXAMINATION_TEMPLATE,
    PRESERVATION_APPLICATION_TEMPLATE,
    LABOR_ARBITRATION_APPLICATION_TEMPLATE,
    LABOR_SUPERVISION_COMPLAINT_TEMPLATE,
    WAGE_DEMAND_LETTER_TEMPLATE,
    FORCED_TERMINATION_NOTICE_TEMPLATE,
    ARBITRATION_AUTHORIZATION_TEMPLATE,
]

# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------

INSERT_SQL = text("""
    INSERT INTO templates (name, type, description, structure, ai_prompt, format_rules, variables, is_public, created_at, updated_at)
    VALUES (:name, :type, :description, :structure, :ai_prompt, :format_rules, :variables, TRUE, :created_at, :updated_at)
""")


def seed_templates() -> None:
    """Insert all default templates into the database, skipping any that already exist.

    Idempotent — safe to run multiple times.  Uses explicit SELECT-before-INSERT
    rather than ON CONFLICT so it works with both SQLite and PostgreSQL.
    """
    # Ensure tables exist first (idempotent).
    try:
        from app.core.database import Base
        import app.models  # noqa: F401
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"  Warning: could not auto-create tables ({e}), continuing...")

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    with Session(engine) as session:
        for tpl in ALL_TEMPLATES:
            try:
                existing = session.execute(
                    text("SELECT id FROM templates WHERE name = :name"),
                    {"name": tpl["name"]},
                ).scalar_one_or_none()

                if existing is not None:
                    print(f"  [skip] {tpl['name']} ({tpl['type']}) -- already exists (id={existing})")
                    skipped += 1
                    continue

                session.execute(
                    INSERT_SQL,
                    {
                        "name": tpl["name"],
                        "type": tpl["type"],
                        "description": tpl["description"],
                        "structure": json.dumps(tpl["structure"], ensure_ascii=False),
                        "ai_prompt": tpl["ai_prompt"],
                        "format_rules": json.dumps(tpl["format_rules"], ensure_ascii=False),
                        "variables": json.dumps(tpl["variables"], ensure_ascii=False),
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                print(f"  [inserted] {tpl['name']} ({tpl['type']})")
                inserted += 1
            except Exception as e:
                print(f"  [error] {tpl['name']} ({tpl['type']}): {e}")
                skipped += 1

        session.commit()

    print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}, Total: {len(ALL_TEMPLATES)}")


if __name__ == "__main__":
    print(f"Seeding document templates into {SYNC_URL} ...\n")
    seed_templates()
