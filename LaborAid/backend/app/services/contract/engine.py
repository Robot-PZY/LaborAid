"""合同智能审查引擎 — 5维度风险分析 + 修改建议 + 报告生成

健壮性增强：
- 处理只识别到1-2个条款的合同
- 处理零风险项（全部条款合规的合同）
- 确保即使单个维度失败也能完成完整审查
"""

import json
import logging
from app.prompts.persona import prompt_with_persona, SYSTEM_CONTRACT
from app.services.llm_client import create_llm_client_from_settings
from app.config import get_settings
from app.schemas.contract import ContractRiskItem

logger = logging.getLogger(__name__)

# Maximum characters for LLM response to prevent runaway output
MAX_LLM_RESPONSE_CHARS = 50000

# Input validation limits
MAX_CONTRACT_LENGTH = 200000  # 200K chars max for contract text
MIN_CONTRACT_LENGTH = 10  # Minimum meaningful contract length

REVIEW_DIMENSIONS = {
    "legality": "合法性",
    "completeness": "完备性",
    "fairness": "公平性",
    "clarity": "明确性",
    "enforceability": "可执行性",
}

# Minimum expected dimensions in a thorough review
_EXPECTED_DIMENSIONS = list(REVIEW_DIMENSIONS.keys())


def _validate_risk_items(raw_items: list) -> list[dict]:
    """Validate and sanitize LLM-returned risk items."""
    valid = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        try:
            validated = ContractRiskItem(
                dimension=str(item.get("dimension", "enforceability")),
                level=str(item.get("level", "low")) if item.get("level") in ("high", "medium", "low") else "low",
                clause=str(item.get("clause", "")),
                issue=str(item.get("issue", "")),
                suggestion=str(item.get("suggestion", "")),
            )
            valid.append(validated.model_dump())
        except Exception:
            continue
    return valid


def _check_dimension_coverage(risk_items: list[dict]) -> list[str]:
    """Check which review dimensions have no risk items identified.

    Returns a list of uncovered dimension keys.
    """
    covered = {item.get("dimension", "") for item in risk_items}
    return [d for d in _EXPECTED_DIMENSIONS if d not in covered]


async def _review_single_dimension(
    client, model: str, dimension_key: str, dimension_name: str,
    clauses_text: str, case_context: str,
) -> dict | None:
    """Review a single dimension independently. Returns a risk item dict or None.

    Used as a fallback when the main review misses a dimension.
    """
    prompt = f"""你是合同审查专家，请仅从「{dimension_name}」角度审查以下合同条款。

审查标准：
- {dimension_name}方面的具体检查要点

{"## 案件背景" if case_context else ""}
{case_context}

## 合同条款
{clauses_text[:10000]}

请以JSON格式返回审查结果：
{{
  "dimension": "{dimension_key}",
  "issues_found": true或false,
  "level": "high|medium|low",
  "clause": "相关条款原文摘要（如有问题）",
  "issue": "具体问题描述（如有）",
  "suggestion": "修改建议（如有）"
}}

如果没有发现{dimension_name}方面的问题，请返回：
{{"dimension": "{dimension_key}", "issues_found": false, "level": "low", "clause": "", "issue": "未发现{dimension_name}方面的问题", "suggestion": ""}}

请直接返回JSON。"""

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip() if response.content else ""
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        if data.get("issues_found", False):
            return {
                "dimension": dimension_key,
                "level": data.get("level", "low"),
                "clause": str(data.get("clause", "")),
                "issue": str(data.get("issue", "")),
                "suggestion": str(data.get("suggestion", "")),
            }
        return None
    except Exception as e:
        logger.warning("Single dimension review failed for %s: %s", dimension_key, e)
        return None


async def review_contract(
    contract_text: str,
    clauses: list[dict] | None = None,
    case_context: str = "",
    llm=None,
) -> dict:
    """
    审查合同，返回 {report, risk_items, risk_score}

    Handles edge cases:
    - Contracts with only 1-2 clauses: still performs full 5-dimension review
    - Contracts with zero risk items: reports as clean with recommendations
    - Individual dimension failures: completes review with partial results
    """
    # Input validation
    if not contract_text or not contract_text.strip():
        return {
            "report": "合同内容为空，无法进行审查。",
            "risk_items": [],
            "risk_score": None,
        }
    if len(contract_text) < MIN_CONTRACT_LENGTH:
        return {
            "report": "合同内容过短，无法进行有效审查，请提供完整的合同文本。",
            "risk_items": [],
            "risk_score": None,
        }
    if len(contract_text) > MAX_CONTRACT_LENGTH:
        logger.warning("Contract text truncated: %d > %d chars", len(contract_text), MAX_CONTRACT_LENGTH)
        contract_text = contract_text[:MAX_CONTRACT_LENGTH]

    settings = get_settings()
    if llm:
        client, model = llm.client, llm.model
    else:
        client = create_llm_client_from_settings(settings)
        model = settings.LLM_MODEL

    clauses_text = ""
    if clauses:
        clauses_text = "\n\n".join(
            f"【{c.get('type', '未知类型')}】(第{c.get('position', i+1)}条)\n{c.get('text', '')}"
            for i, c in enumerate(clauses)
        )

    # If no identifiable clauses or very few, send the full contract text
    if not clauses_text:
        clauses_text = contract_text[:15000] if contract_text else "（合同内容为空）"
    elif len(clauses) <= 2:
        # For contracts with only 1-2 clauses, include full text for context
        full_context = contract_text[:15000] if contract_text else clauses_text
        clauses_text = f"## 已识别条款：\n{clauses_text}\n\n## 合同全文：\n{full_context}"

    prompt = prompt_with_persona(f"""请对以下合同进行全面审查。

## 审查维度
1. **合法性** — 条款是否违反强制性法律规定
2. **完备性** — 是否缺少必要条款（违约责任、争议解决、知识产权、保密条款等）
3. **公平性** — 权利义务是否明显失衡，是否存在霸王条款
4. **明确性** — 表述是否清晰无歧义，关键条款是否具体可量化
5. **可执行性** — 条款是否具备实际可操作性，履行标准是否明确

{"## 案件背景" if case_context else ""}
{case_context}

## 合同条款
{clauses_text}

## 审查要求
请以JSON格式返回审查结果，结构如下：
{{
  "risk_items": [
    {{
      "dimension": "legality|completeness|fairness|clarity|enforceability",
      "level": "high|medium|low",
      "clause": "相关条款原文摘要",
      "issue": "具体问题描述",
      "suggestion": "修改建议（包含具体修改后的条款文字）"
    }}
  ],
  "summary": "整体审查摘要（200字以内）",
  "risk_score": 75,
  "recommendations": ["建议1", "建议2", ...],
  "missing_clauses": ["缺少的必要条款类型列表"]
}}

注意：
- risk_score 范围 0-100，越高表示风险越大
- 每个风险项必须给出具体的修改建议文字
- 如果合同有明显违法条款，标记为 high 级别
- 检查是否缺少常见必要条款
- **必须覆盖所有5个审查维度，即使某个维度没有发现问题也要列出低风险项**
- **如果合同内容很少或只有1-2个条款，请基于合同全文进行分析，同时指出合同内容不完整的问题**

请直接返回JSON，不要包含其他文字。""")

    raw_text = ""
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=SYSTEM_CONTRACT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip() if response.content else ""
        # Max length protection
        if len(raw_text) > MAX_LLM_RESPONSE_CHARS:
            logger.warning("LLM response truncated: %d > %d", len(raw_text), MAX_LLM_RESPONSE_CHARS)
            raw_text = raw_text[:MAX_LLM_RESPONSE_CHARS]
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.warning("AI contract review JSON parse failed: %s", e)
        result = {
            "risk_items": [],
            "summary": f"审查引擎返回格式异常，原始响应:\n{raw_text[:2000]}",
            "risk_score": None,
            "recommendations": [],
            "missing_clauses": [],
        }
    except Exception as e:
        logger.error("AI contract review call failed: %s", e)
        return {
            "report": f"审查服务暂时不可用，请稍后重试。",
            "risk_items": [],
            "risk_score": None,
        }

    # Validate risk items from LLM output
    risk_items = _validate_risk_items(result.get("risk_items", []))

    # Check dimension coverage and fill gaps with individual dimension reviews
    uncovered = _check_dimension_coverage(risk_items)
    if uncovered:
        logger.info("Review missed dimensions: %s, running individual dimension reviews", uncovered)
        dimension_tasks = []
        for dim_key in uncovered:
            dimension_tasks.append(
                _review_single_dimension(client, model, dim_key, REVIEW_DIMENSIONS[dim_key],
                                         clauses_text, case_context)
            )
        dimension_results = await __import__('asyncio').gather(*dimension_tasks, return_exceptions=True)
        for dim_result in dimension_results:
            if isinstance(dim_result, dict) and dim_result:
                risk_items.append(dim_result)

    # Handle zero risk items (clean contract)
    if not risk_items:
        logger.info("No risk items found - contract appears clean")
        # Add a minimal informational item so the report is not empty
        risk_items = [{
            "dimension": "completeness",
            "level": "low",
            "clause": "",
            "issue": "未发现明显风险条款",
            "suggestion": "建议由专业律师进行人工复核确认",
        }]

    # Sanitize risk_score — handle None, NaN, out-of-range, and edge cases
    try:
        risk_score = result.get("risk_score")
        if risk_score is None:
            # Infer score from risk items if LLM didn't return one
            if not risk_items:
                risk_score = 0.0
            else:
                high = sum(1 for r in risk_items if r.get("level") == "high")
                medium = sum(1 for r in risk_items if r.get("level") == "medium")
                low = sum(1 for r in risk_items if r.get("level") == "low")
                risk_score = min(100.0, high * 30 + medium * 15 + low * 5)
        else:
            risk_score = float(risk_score)
        # Clamp to valid range
        if risk_score != risk_score:  # NaN check
            risk_score = 0.0
        risk_score = max(0.0, min(100.0, risk_score))
    except (TypeError, ValueError):
        risk_score = 0.0

    # For contracts with very few clauses, note this in the report
    clause_count = len(clauses) if clauses else 0
    if clause_count <= 2:
        if not result.get("summary"):
            result["summary"] = ""
        result["summary"] = (
            f"[注：仅识别到{clause_count}个条款，以下为基于合同全文的分析。"
            f"建议补充完整合同内容后重新审查。]\n" + result["summary"]
        )

    result["risk_items"] = risk_items
    result["risk_score"] = risk_score

    report = _build_report(result)
    return {
        "report": report,
        "risk_items": risk_items,
        "risk_score": risk_score,
    }


def _build_report(result: dict) -> str:
    """将审查结果转为可读的报告文本"""
    parts = []

    summary = result.get("summary", "")
    score = result.get("risk_score")
    if score is not None:
        level = "低风险" if score < 30 else "中等风险" if score < 60 else "高风险" if score < 80 else "极高风险"
        parts.append(f"# 合同审查报告\n")
        parts.append(f"**风险等级**: {level}（评分: {score}/100）\n")
    parts.append(f"\n{summary}\n")

    # Dimension coverage summary
    risk_items = result.get("risk_items", [])
    if risk_items:
        dimensions_covered = set(item.get("dimension", "") for item in risk_items)
        dim_names = [REVIEW_DIMENSIONS.get(d, d) for d in dimensions_covered if d in REVIEW_DIMENSIONS]
        if dim_names:
            parts.append(f"\n**审查维度覆盖**: {'、'.join(dim_names)}\n")

    # Risk items grouped by dimension
    if risk_items:
        parts.append("\n---\n\n## 风险项详情\n")

        high_items = [r for r in risk_items if r.get("level") == "high"]
        medium_items = [r for r in risk_items if r.get("level") == "medium"]
        low_items = [r for r in risk_items if r.get("level") == "low"]

        for level_name, items in [("高风险", high_items), ("中等风险", medium_items), ("低风险", low_items)]:
            if not items:
                continue
            parts.append(f"\n### {level_name}\n")
            for i, item in enumerate(items, 1):
                dim = REVIEW_DIMENSIONS.get(item.get("dimension", ""), item.get("dimension", ""))
                parts.append(f"\n**{i}. [{dim}]** {item.get('issue', '')}\n")
                clause = item.get("clause", "")
                if clause:
                    parts.append(f"> 相关条款: {clause}\n")
                suggestion = item.get("suggestion", "")
                if suggestion:
                    parts.append(f"- 修改建议: {suggestion}\n")

    # Missing clauses
    missing = result.get("missing_clauses", [])
    if missing:
        parts.append("\n---\n\n## 缺少的必要条款\n")
        for m in missing:
            parts.append(f"- {m}\n")

    # Recommendations
    recs = result.get("recommendations", [])
    if recs:
        parts.append("\n---\n\n## 综合建议\n")
        for r in recs:
            parts.append(f"- {r}\n")

    return "\n".join(parts)
