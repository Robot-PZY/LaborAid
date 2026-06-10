"""证据链分析服务 — 分析案件证据完整性，识别缺失环节"""

import asyncio
import json
import logging
from app.prompts.persona import prompt_with_persona, SYSTEM_EVIDENCE, SYSTEM_CROSS_EXAM
from app.services.llm_client import create_llm_client_from_settings
from app.config import get_settings

logger = logging.getLogger(__name__)

# Timeout for LLM calls in seconds.
_LLM_TIMEOUT = 180

# Maximum response length (safety cap).
_MAX_RESPONSE_LENGTH = 32000

# Maximum number of evidence items to include in prompt.
_MAX_EVIDENCE_ITEMS = 50

# Maximum length for individual evidence text.
_MAX_EVIDENCE_TEXT_LENGTH = 100000

# Maximum length for case description.
_MAX_CASE_DESC_LENGTH = 50000


async def analyze_evidence_chain(
    case_description: str,
    evidence_list: list[dict],
    llm=None,
) -> dict:
    """
    分析证据链完整性。
    evidence_list: [{id, title, type, ocr_text, analysis, tags}]
    返回: {chain_report, completeness_score, missing_evidence, timeline}
    """
    # Guard: empty evidence list — return a minimal report.
    if not evidence_list:
        return {
            "chain_report": "# 证据链分析报告\n\n**完整度**: 0/100 — 无证据\n\n当前案件尚未录入任何证据材料，无法进行证据链分析。请先上传并录入证据。",
            "completeness_score": 0,
            "chain_status": "无证据",
            "missing_evidence": [],
        }

    # Guard: empty case description.
    if not case_description or not case_description.strip():
        case_description = "（未提供案件描述）"
    elif len(case_description) > _MAX_CASE_DESC_LENGTH:
        logger.warning("Case description truncated: %d > %d chars", len(case_description), _MAX_CASE_DESC_LENGTH)
        case_description = case_description[:_MAX_CASE_DESC_LENGTH]

    settings = get_settings()
    if llm:
        client, model = llm.client, llm.model
        max_tokens = min(llm.max_tokens, 8192)
    else:
        client = create_llm_client_from_settings(settings)
        model = settings.LLM_MODEL
        max_tokens = 8192

    # Build evidence summary, truncating per-item text.
    evidence_summary = []
    for ev in evidence_list[:_MAX_EVIDENCE_ITEMS]:
        ocr_text = ev.get("ocr_text") or ""
        if len(ocr_text) > _MAX_EVIDENCE_TEXT_LENGTH:
            ocr_text = ocr_text[:_MAX_EVIDENCE_TEXT_LENGTH]
        text_preview = ocr_text[:500]
        analysis_text = ev.get("analysis") or ""
        if len(analysis_text) > _MAX_EVIDENCE_TEXT_LENGTH:
            analysis_text = analysis_text[:_MAX_EVIDENCE_TEXT_LENGTH]
        analysis_preview = analysis_text[:300]
        evidence_summary.append({
            "id": ev.get("id"),
            "title": ev.get("title", ""),
            "type": ev.get("type", ""),
            "tags": ev.get("tags", []),
            "text_preview": text_preview,
            "analysis_preview": analysis_preview,
        })

    prompt = prompt_with_persona(f"""请对以下案件的证据链进行完整性分析。

## 案件描述
{case_description[:3000]}

## 已有证据（{len(evidence_summary)}份）
{json.dumps(evidence_summary, ensure_ascii=False, indent=2)}

## 分析要求

请从以下角度分析证据链：

1. **证据链完整性**：现有证据能否形成完整的证明链？是否存在断链？
2. **待证事实覆盖**：案件的核心待证事实有哪些？每项待证事实是否有足够证据支撑？
3. **证据矛盾**：各证据之间是否存在矛盾或冲突？
4. **缺失证据**：还需要补充哪些类型的证据？
5. **证据排序建议**：建议的举证顺序

请以JSON格式返回：
{{
  "completeness_score": 75,
  "chain_status": "基本完整|存在缺口|严重不足",
  "facts_to_prove": [
    {{"fact": "待证事实描述", "supported": true, "supporting_evidence": [证据ID列表], "gap": ""}}
  ],
  "contradictions": ["矛盾1", "矛盾2"],
  "missing_evidence": [
    {{"type": "需要的证据类型", "purpose": "证明什么", "urgency": "high|medium|low"}}
  ],
  "timeline": [
    {{"date": "YYYY-MM-DD或描述", "event": "事件描述", "evidence_id": null, "confidence": "high|medium|low"}}
  ],
  "suggested_order": [证据ID的举证顺序],
  "summary": "整体分析摘要（200字以内）"
}}

请直接返回JSON，不要包含其他文字。chain_report 将由系统根据 JSON 生成，summary 务必简洁。""")

    raw = ""
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_EVIDENCE,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_LLM_TIMEOUT,
        )
        raw = response.content[0].text.strip()
        # Safety cap.
        if len(raw) > _MAX_RESPONSE_LENGTH:
            raw = raw[:_MAX_RESPONSE_LENGTH]
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
    except asyncio.TimeoutError:
        logger.warning("Evidence chain analysis timed out after %ds", _LLM_TIMEOUT)
        result = {
            "completeness_score": None,
            "chain_status": "分析超时",
            "facts_to_prove": [],
            "contradictions": [],
            "missing_evidence": [],
            "suggested_order": [],
            "summary": f"证据链分析超时（{_LLM_TIMEOUT}秒），请稍后重试。",
        }
    except json.JSONDecodeError as e:
        logger.warning(f"Evidence chain analysis JSON parse failed: {e}")
        result = {
            "completeness_score": None,
            "chain_status": "分析失败",
            "facts_to_prove": [],
            "contradictions": [],
            "missing_evidence": [],
            "suggested_order": [],
            "summary": "证据链分析结果解析失败，请稍后重试。",
        }
    except (ConnectionError, OSError) as e:
        logger.warning(f"Evidence chain analysis connection failed: {e}")
        result = {
            "completeness_score": None,
            "chain_status": "分析失败",
            "facts_to_prove": [],
            "contradictions": [],
            "missing_evidence": [],
            "suggested_order": [],
            "summary": "证据链分析服务连接失败，请检查网络配置或联系管理员。",
        }
    except Exception as e:
        logger.warning(f"Evidence chain analysis failed: {e}")
        result = {
            "completeness_score": None,
            "chain_status": "分析失败",
            "facts_to_prove": [],
            "contradictions": [],
            "missing_evidence": [],
            "suggested_order": [],
            "summary": "证据链分析服务暂时不可用，请稍后重试。",
        }

    # Build readable report
    report = _build_chain_report(result)
    return {
        "chain_report": report,
        "completeness_score": result.get("completeness_score"),
        "chain_status": result.get("chain_status", "未知"),
        "missing_evidence": result.get("missing_evidence", []),
        "timeline": result.get("timeline", []),
        "credibility": {
            "score": min(1.0, max(0.0, (result.get("completeness_score") or 50) / 100)),
            "needs_human_review": True,
            "reason": "证据链分析为 AI 辅助，关键事实请人工核对",
        },
    }


async def generate_cross_examination(
    evidence_text: str,
    evidence_type: str,
    case_context: str,
    our_side: str = "被告",
    llm=None,
) -> str:
    """为对方证据生成质证意见"""
    # Guard: empty evidence text.
    if not evidence_text or not evidence_text.strip():
        return "无法生成质证意见：证据内容为空"

    # Guard: evidence text too long.
    if len(evidence_text) > _MAX_EVIDENCE_TEXT_LENGTH:
        logger.warning("Evidence text truncated for cross-examination: %d > %d", len(evidence_text), _MAX_EVIDENCE_TEXT_LENGTH)
        evidence_text = evidence_text[:_MAX_EVIDENCE_TEXT_LENGTH]

    # Guard: validate evidence_type.
    valid_types = {"书证", "物证", "视听资料", "电子数据", "证人证言", "当事人陈述", "鉴定意见", "勘验笔录", "其他"}
    if not evidence_type or not evidence_type.strip():
        evidence_type = "其他"

    settings = get_settings()
    if llm:
        client, model = llm.client, llm.model
        max_tokens = min(llm.max_tokens, 4096)
    else:
        client = create_llm_client_from_settings(settings)
        model = settings.LLM_MODEL
        max_tokens = 4096

    effective_context = case_context[:3000] if case_context else "未提供案件背景"

    prompt = prompt_with_persona(f"""{our_side}方代理人。请针对以下对方提交的证据，从真实性、合法性、关联性三个维度撰写质证意见。

## 对方证据
类型：{evidence_type}
内容：
{evidence_text[:8000]}

## 案件背景
{effective_context}

## 质证要求

请从以下维度逐一质证：
1. **真实性**：证据是否真实，是否有伪造或变造的可能
2. **合法性**：证据收集方式是否合法，是否存在非法证据排除情形
3. **关联性**：证据与案件待证事实的关联程度
4. **证明力**：即使证据三性没有问题，其证明力大小如何

请输出完整的质证意见，语言专业有力，适当引用法条。""")

    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_CROSS_EXAM,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_LLM_TIMEOUT,
        )
        result = response.content[0].text if response.content else "质证意见生成失败"
        if len(result) > _MAX_RESPONSE_LENGTH:
            result = result[:_MAX_RESPONSE_LENGTH] + "\n\n[... 结果过长，已截断]"
        return result
    except asyncio.TimeoutError:
        logger.warning("Cross-examination generation timed out")
        return "质证意见生成超时，请稍后重试。"
    except (ConnectionError, OSError) as e:
        logger.warning(f"Cross-examination generation connection failed: {e}")
        return "质证意见生成失败：无法连接到 AI 服务，请检查网络配置或联系管理员。"
    except Exception as e:
        logger.warning(f"Cross-examination generation failed: {e}")
        return "质证意见生成失败，请稍后重试。"


def _build_chain_report(result: dict) -> str:
    parts = []

    score = result.get("completeness_score")
    status = result.get("chain_status", "未知")
    if score is not None:
        parts.append(f"# 证据链分析报告\n\n")
        parts.append(f"**完整度**：{score}/100 · {status}\n\n")
    summary = (result.get("summary") or "").strip()
    if summary:
        parts.append(f"{summary[:400]}\n")

    facts = result.get("facts_to_prove", [])
    if facts:
        parts.append("\n---\n\n## 待证事实覆盖\n")
        for f in facts:
            mark = "已证明" if f.get("supported") else "待补充"
            parts.append(f"- **{f.get('fact', '')}** [{mark}]\n")
            if f.get("gap"):
                parts.append(f"  缺口: {f['gap']}\n")

    contradictions = result.get("contradictions", [])
    if contradictions:
        parts.append("\n---\n\n## 证据矛盾\n")
        for c in contradictions:
            parts.append(f"- {c}\n")

    missing = result.get("missing_evidence", [])
    if missing:
        parts.append("\n---\n\n## 需要补充的证据\n")
        for m in missing:
            urgency = {"high": "紧急", "medium": "一般", "low": "可选"}.get(m.get("urgency", "low"), "一般")
            parts.append(f"- **[{urgency}]** {m.get('type', '')} — {m.get('purpose', '')}\n")

    return "\n".join(parts)
