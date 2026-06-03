"""案件维权助手问答 — 基于案件上下文的短回答。"""

from __future__ import annotations

import json
import logging
import re

from app.services.orchestrator.case_context import CaseWorkContext
from app.services.orchestrator.context_summary import build_case_context_text
from app.services.orchestrator.next_step import compute_case_next_step

logger = logging.getLogger(__name__)

_SYSTEM = """你是 LaborAid 劳动者维权平台的智能助手。根据用户案件材料状态回答问题。

要求：
1. 用简洁中文，3–6 句话为主，必要时用条目
2. 明确建议下一步去哪个模块（证据/文书/指引/案情分析）
3. 不得声称已代理用户立案、投诉或保证胜诉
4. 结尾一句提醒：不构成法律意见，重要事项请咨询12348或当地人社

若信息不足，如实说明还需补充什么材料。"""


async def answer_case_question(
    ctx: CaseWorkContext,
    question: str,
    *,
    llm,
) -> dict:
    base_step = compute_case_next_step(ctx)
    ctx_text = build_case_context_text(ctx)
    fallback = _fallback_answer(ctx, question, base_step)

    if not llm or not getattr(llm, "client", None):
        return fallback

    try:
        prompt = f"""【案件材料】
{ctx_text}

【系统建议的下一步】
{base_step['label']}：{base_step['reason']}
推荐路由：{base_step['route']}

【用户问题】
{question.strip()}

请回答用户问题，并说明与建议下一步是否一致。返回 JSON：
{{
  "answer": "回答正文",
  "suggested_route": "/path 或空字符串",
  "aligns_with_next_step": true/false
}}"""

        response = await llm.client.messages.create(
            model=llm.model,
            max_tokens=min(800, llm.max_tokens),
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        if response.content:
            text = (response.content[0].text or "").strip()
        data = _parse_json(text)
        if data and data.get("answer"):
            route = (data.get("suggested_route") or "").strip() or base_step["route"]
            return {
                "answer": str(data["answer"]).strip(),
                "suggested_route": route,
                "suggested_label": base_step["label"],
                "pipeline_stage": base_step["pipeline_stage"],
                "used_llm": True,
            }
    except Exception as e:
        logger.warning("Case agent ask LLM failed: %s", e)

    return {**fallback, "used_llm": False}


def _fallback_answer(ctx: CaseWorkContext, question: str, base_step: dict) -> dict:
    r = ctx.readiness
    q = question.strip()
    answer_parts = [f"关于「{q[:40]}{'…' if len(q) > 40 else ''}」："]

    if "证据" in q or "材料" in q:
        miss = [s.item for s in (r.evidence_suggestions or []) if s.status == "missing"][:3]
        if miss:
            answer_parts.append(f"建议优先补充：{'、'.join(miss)}。")
        elif ctx.evidence_count == 0:
            answer_parts.append("请先上传工资流水、合同或沟通记录等核心证据。")
        else:
            answer_parts.append(f"已上传 {ctx.evidence_count} 份证据，可运行证据链分析查漏。")
    elif "文书" in q or "申请" in q:
        if r.docgen_ready:
            answer_parts.append("材料基础可支撑文书生成，请进入文书模块并人工核对。")
        else:
            answer_parts.append("文书条件尚未满足：" + "；".join(r.docgen_blockers[:2] or ["先补证据与案情"]))
    else:
        answer_parts.append(r.summary)
        answer_parts.append(f"当前建议：{base_step['explanation']}")

    return {
        "answer": "".join(answer_parts),
        "suggested_route": base_step["route"],
        "suggested_label": base_step["label"],
        "pipeline_stage": base_step["pipeline_stage"],
        "used_llm": False,
    }


def _parse_json(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None
