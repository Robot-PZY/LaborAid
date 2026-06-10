"""内容质量检查 — 检测文书长度、结构完整性并生成警告。"""

import re
from typing import Any

# 各文书类型的最低字数要求
MIN_CONTENT_LENGTH = {
    "application": 800,          # 仲裁申请书
    "complaint": 800,            # 民事起诉状
    "labor_supervision": 600,    # 劳动监察投诉书
    "defense": 600,              # 答辩状
    "appeal": 700,               # 上诉状
    "lawyer_letter": 500,        # 律师函
    "settlement_agreement": 700, # 和解协议
    "mediation_agreement": 600,  # 调解协议
    "evidence_list": 300,        # 证据清单
    "legal_opinion": 800,        # 法律意见书
    "wage_demand_letter": 500,   # 工资催款函
    "forced_termination_notice": 500,  # 被迫解除劳动合同通知书
    "arbitration_result": 400,   # 仲裁结果分析
    "case_analysis": 600,        # 案件分析报告
}

# 各文书类型的必要章节关键词
REQUIRED_SECTIONS = {
    "application": ["仲裁请求", "事实与理由"],
    "complaint": ["诉讼请求", "事实与理由"],
    "labor_supervision": ["投诉请求", "事实与理由"],
    "defense": ["答辩请求", "答辩理由"],
    "appeal": ["上诉请求", "上诉理由"],
    "lawyer_letter": ["事实", "法律分析", "要求"],
    "settlement_agreement": ["协议内容", "双方签字"],
    "mediation_agreement": ["调解协议", "双方签字"],
    "evidence_list": ["证据清单", "证明目的"],
    "legal_opinion": ["法律分析", "法律意见"],
    "wage_demand_letter": ["欠款事实", "要求"],
    "forced_termination_notice": ["解除理由", "法律依据"],
}


def check_content_length(content: str, doc_type: str) -> dict[str, Any]:
    """检查文书内容长度是否达标。"""
    if not content:
        return {
            "passed": False,
            "actual_length": 0,
            "min_length": MIN_CONTENT_LENGTH.get(doc_type, 500),
            "message": "文书内容为空",
        }

    # 统计实际字数（去除 Markdown 标记）
    plain_text = re.sub(r"[#*\-\[\]\(\)\|`]", "", content)
    plain_text = re.sub(r"\s+", "", plain_text)
    actual_length = len(plain_text)

    min_length = MIN_CONTENT_LENGTH.get(doc_type, 500)
    passed = actual_length >= min_length

    return {
        "passed": passed,
        "actual_length": actual_length,
        "min_length": min_length,
        "message": f"内容长度{'达标' if passed else '不足'}：{actual_length}字（要求≥{min_length}字）",
    }


def check_required_sections(content: str, doc_type: str) -> dict[str, Any]:
    """检查文书是否包含必要章节。"""
    required = REQUIRED_SECTIONS.get(doc_type, [])
    if not required:
        return {
            "passed": True,
            "missing": [],
            "message": "该文书类型无特定章节要求",
        }

    missing = []
    for section_keyword in required:
        # 检查章节关键词是否出现在内容中
        if section_keyword not in content:
            missing.append(section_keyword)

    passed = len(missing) == 0
    return {
        "passed": passed,
        "missing": missing,
        "message": f"{'所有章节完整' if passed else f'缺少章节：{', '.join(missing)}'}",
    }


def check_legal_citations(content: str) -> dict[str, Any]:
    """检查法条引用是否规范。"""
    # 查找《》标记的法律名称
    law_pattern = r"《([^》]+)》"
    laws = re.findall(law_pattern, content)

    # 查找"第X条"格式的条文引用
    article_pattern = r"第[零一二三四五六七八九十百千\d]+条"
    articles = re.findall(article_pattern, content)

    has_citations = len(laws) > 0 or len(articles) > 0

    return {
        "passed": has_citations,
        "law_count": len(laws),
        "article_count": len(articles),
        "message": f"引用法律{len(laws)}部、条文{len(articles)}条" if has_citations else "未发现法条引用",
    }


def check_template_variable_fill_rate(doc_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """检查模板变量的填充率，确保关键变量已填充。"""
    try:
        from app.services.docgen.templates.legal_templates import get_template_variables
    except ImportError:
        return {
            "passed": True,
            "fill_rate": 1.0,
            "message": "模板变量检查跳过（未找到模板模块）",
        }

    template_vars = get_template_variables(doc_type)
    if not template_vars:
        return {
            "passed": True,
            "fill_rate": 1.0,
            "message": "该文书类型无模板变量要求",
        }

    # 统计已填充的变量
    filled_vars = []
    empty_vars = []
    for var in template_vars:
        value = payload.get(var, "")
        # 检查是否为空或占位符
        if not value or value == "[待填写]" or value == PLACEHOLDER:
            empty_vars.append(var)
        else:
            filled_vars.append(var)

    fill_rate = len(filled_vars) / len(template_vars) if template_vars else 1.0
    passed = fill_rate >= 0.6  # 至少填充 60% 的变量

    return {
        "passed": passed,
        "fill_rate": fill_rate,
        "filled_count": len(filled_vars),
        "total_count": len(template_vars),
        "empty_vars": empty_vars[:5],  # 最多返回 5 个未填充的变量名
        "message": f"模板变量填充率 {fill_rate:.0%}（{len(filled_vars)}/{len(template_vars)}）" + (
            "" if passed else f"，缺失关键变量：{', '.join(empty_vars[:3])}"
        ),
    }


def run_quality_checks(content: str, doc_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """运行所有质量检查，返回综合结果。"""
    length_check = check_content_length(content, doc_type)
    section_check = check_required_sections(content, doc_type)
    citation_check = check_legal_citations(content)
    
    # 模板变量填充率检查（如果提供了 payload）
    fill_rate_check = None
    if payload is not None:
        fill_rate_check = check_template_variable_fill_rate(doc_type, payload)

    all_passed = (
        length_check["passed"]
        and section_check["passed"]
        and citation_check["passed"]
        and (fill_rate_check["passed"] if fill_rate_check else True)
    )

    warnings = []
    if not length_check["passed"]:
        warnings.append(length_check["message"])
    if not section_check["passed"]:
        warnings.append(section_check["message"])
    if not citation_check["passed"]:
        warnings.append(citation_check["message"])
    if fill_rate_check and not fill_rate_check["passed"]:
        warnings.append(fill_rate_check["message"])

    return {
        "passed": all_passed,
        "warnings": warnings,
        "checks": {
            "length": length_check,
            "sections": section_check,
            "citations": citation_check,
            **({"fill_rate": fill_rate_check} if fill_rate_check else {}),
        },
    }
