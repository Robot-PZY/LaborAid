"""维权前台 — 案情分析与工具分流。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.intake.config_loader import (
    get_causes,
    get_evidence_checklists,
    get_guidance_links,
)
from app.services.intake.plan_builder import (
    _case_title_with_date,
    build_action_plan,
    plan_to_recommended_tools,
)
from app.services.llm_client import create_llm_client_from_settings
from app.config import get_settings

logger = logging.getLogger(__name__)

# agent_id 与前端 agents.ts 一致
_CAUSE_KEYWORDS: dict[str, list[str]] = {
    "wage_arrears": ["拖欠", "欠薪", "不发工资", "工资没发", "讨薪", "欠工资", "克扣"],
    "illegal_termination": ["辞退", "开除", "解雇", "解除", "裁员", "被迫离职", "违法解除", "辞退"],
    "overtime_pay": ["加班", "加班费", "超时", "休息日上班"],
    "no_written_contract": ["没签合同", "未签合同", "没有合同", "二倍工资", "书面合同"],
}

_CHANNEL_KEYWORDS: dict[str, list[str]] = {
    "migrant-worker": ["农民工", "包工头", "工地", "欠薪"],
    "intern-probation": ["实习生", "试用期", "实习", "毕业生", "实习协议"],
    "female-worker": ["女职工", "怀孕", "孕期", "产假", "生育", "三期", "哺乳", "妇联"],
    "gig-worker": ["骑手", "外卖", "网约车", "快递", "平台", "接单", "派单", "封号", "限制接单", "降单价", "灵活用工", "新就业形态"],
    "labor-dispatch": ["派遣", "劳务派遣", "派遣工", "派遣公司", "用工单位", "同工同酬", "退回"],
    "work-injury": ["工伤", "受伤", "职业病", "劳动能力鉴定", "伤残", "工伤认定", "工伤赔偿"],
}

_SCENARIO_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "migrant-worker": {
        "wage_boss": ["包工头", "工头", "班组长", "小老板", "欠条"],
        "subcontract": ["分包", "转包", "总包", "劳务公司", "不知告谁"],
        "project_stop": ["停工", "烂尾", "跑路", "老板跑"],
        "after_inspection": ["监察", "已投诉", "举报过", "仍不支付"],
    },
    "intern-probation": {
        "intern_identity": ["在校", "实习协议", "三方协议", "毕业生", "毕业证", "劳动关系"],
        "probation_fire": ["试用期", "不能胜任", "口头辞退", "解除", "辞退"],
        "intern_no_pay": ["实习补贴", "实习报酬", "实习工资", "补贴", "3000"],
    },
    "female-worker": {
        "pregnancy_transfer": ["怀孕", "孕期", "调岗", "降薪"],
        "maternity_leave": ["产假", "生育津贴", "哺乳"],
        "illegal_termination": ["三期", "产期", "哺乳期", "怀孕", "生育"],
    },
    "gig-worker": {
        "platform_relationship": ["劳动关系", "算不算", "认定", "协议", "合作"],
        "gig_injury": ["受伤", "事故", "工伤", "赔偿", "保险"],
        "gig_pay": ["降单价", "扣款", "拖欠", "报酬", "结算"],
        "account_ban": ["封号", "限制接单", "封禁", "账号"],
    },
    "labor-dispatch": {
        "dispatch_equality": ["同工同酬", "工资低", "待遇不同", "正式工"],
        "dispatch_return": ["退回", "派遣公司", "解除", "降薪"],
        "dispatch_fake": ["假派遣", "真用工", "资质", "派遣许可"],
        "dispatch_fire": ["解除", "辞退", "违法", "赔偿金"],
    },
    "work-injury": {
        "injury_recognize": ["工伤认定", "认定", "人社局", "申请"],
        "injury_compensation": ["赔偿", "金额", "争议", "标准", "伤残"],
        "injury_no_insurance": ["没缴", "未缴", "没保险", "未参保"],
        "occupational_disease": ["职业病", "粉尘", "噪音", "有害物质", "诊断"],
    },
}

_DOC_TYPE_MAP = {
    "wage_arrears": "application",
    "illegal_termination": "application",
    "overtime_pay": "application",
    "no_written_contract": "application",
    "gig_pay": "application",
    "gig_injury": "application",
    "account_ban": "application",
    "dispatch_equality": "application",
    "dispatch_return": "application",
    "dispatch_fake": "application",
    "dispatch_fire": "application",
    "injury_compensation": "application",
    "injury_no_insurance": "application",
    "occupational_disease": "application",
}

_BUNDLE_TYPE_LABELS: dict[str, list[str]] = {
    "wage_arrears": ["application", "evidence_list"],
    "illegal_termination": ["application", "forced_termination_notice", "evidence_list"],
    "overtime_pay": ["application", "evidence_list"],
    "no_written_contract": ["application", "evidence_list"],
    "gig_pay": ["application", "evidence_list"],
    "gig_injury": ["application", "evidence_list"],
    "dispatch_equality": ["application", "evidence_list"],
    "dispatch_return": ["application", "evidence_list"],
    "dispatch_fake": ["application", "evidence_list"],
    "dispatch_fire": ["application", "evidence_list"],
    "injury_compensation": ["application", "evidence_list"],
    "injury_no_insurance": ["application", "evidence_list"],
    "occupational_disease": ["application", "evidence_list"],
}


def _recommend_docgen_prefill(
    cause_type: str,
    combined: str,
    summary: str,
) -> dict[str, Any]:
    text = combined or summary
    base_doc_type = _DOC_TYPE_MAP.get(cause_type, "application")
    trigger_keywords = [
        "一并", "同时", "全部", "多份", "批量", "打包", "套装", "一起生成", "顺便",
        "申请书", "证据清单", "催告函", "监察投诉",
    ]
    wants_bundle = any(kw in text for kw in trigger_keywords)
    if cause_type == "wage_arrears" and any(kw in text for kw in ["包工头", "工地", "欠薪"]):
        wants_bundle = True
    if cause_type == "illegal_termination" and any(kw in text for kw in ["被迫解除", "违法解除"]):
        wants_bundle = True

    if not wants_bundle:
        return {
            "docType": base_doc_type,
            "docMode": "single",
            "bundleDocTypes": [],
        }

    bundle_types = _BUNDLE_TYPE_LABELS.get(cause_type, [base_doc_type, "evidence_list"])
    # 去重并保序
    deduped = list(dict.fromkeys(bundle_types))
    return {
        "docType": deduped[0],
        "docMode": "bundle",
        "bundleDocTypes": deduped,
    }


def _match_cause(text: str) -> str:
    lowered = text.lower()
    best = "wage_arrears"
    best_score = 0
    for cause_id, keywords in _CAUSE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lowered)
        if score > best_score:
            best_score = score
            best = cause_id
    return best


def _match_scenario(channel_id: str | None, text: str) -> str | None:
    if not channel_id:
        return None
    scenarios = _SCENARIO_KEYWORDS.get(channel_id)
    if not scenarios:
        return None
    best_id = None
    best_score = 0
    for scenario_id, keywords in scenarios.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_id = scenario_id
    return best_id if best_score > 0 else None


def _match_channel(text: str) -> str | None:
    lowered = text.lower()
    for channel_id, keywords in _CHANNEL_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return channel_id
    return None


def _cause_label(cause_type: str) -> str:
    for c in get_causes():
        if c.get("id") == cause_type:
            return c.get("label") or cause_type
    return cause_type


def _build_tools(
    cause_type: str,
    summary: str,
    description: str,
    parties: dict,
    channel_id: str | None,
    scenario_id: str | None = None,
) -> list[dict]:
    checklist_data = get_evidence_checklists().get(cause_type, {})
    checklist = list(checklist_data.get("required") or [])[:6]
    doc_prefill = _recommend_docgen_prefill(cause_type, description or summary, summary)

    tools: list[dict] = [
        {
            "agent_id": "cases",
            "priority": 1,
            "reason": "先建立案件档案，后续证据与文书都挂在同一案件下",
            "action": "create_case",
            "prefill": {
                "title": _case_title_with_date(f"{_cause_label(cause_type)}维权"),
                "case_type": "administrative_labor",
                "description": description or summary,
                "plaintiff": parties.get("plaintiff"),
                "defendant": parties.get("defendant"),
            },
        },
        {
            "agent_id": "evidence",
            "priority": 2,
            "reason": "上传工资条、流水、聊天截图等，证明事实经过",
            "action": "navigate",
            "prefill": {"checklist": checklist},
        },
        {
            "agent_id": "docgen",
            "priority": 3,
            "reason": "证据整理后可生成仲裁申请书、证据清单",
            "action": "navigate",
            "prefill": {
                "docType": doc_prefill["docType"],
                "docMode": doc_prefill["docMode"],
                "bundleDocTypes": doc_prefill["bundleDocTypes"],
                "caseFacts": description or summary,
            },
        },
        {
            "agent_id": "research",
            "priority": 4,
            "reason": "材料齐备后可生成阶段维权分析报告",
            "action": "navigate",
            "prefill": {},
        },
    ]

    if any(kw in (description or summary) for kw in ["合同", "协议", "劳动合同"]):
        tools.insert(2, {
            "agent_id": "contract",
            "priority": 3,
            "reason": "检测到合同相关描述，可先审查合同风险条款",
            "action": "navigate",
            "prefill": {},
        })
        for t in tools[3:]:
            t["priority"] += 1

    return sorted(tools, key=lambda x: x["priority"])


def _default_missing(cause_type: str, text: str) -> list[str]:
    missing = []
    if not re.search(r"\d+元|\d+万|金额|工资", text):
        missing.append("具体争议金额或欠薪数额")
    if "公司" not in text and "单位" not in text and "老板" not in text:
        missing.append("用人单位全称")
    if cause_type == "wage_arrears" and "月" not in text:
        missing.append("欠薪发生的月份或期间")
    if cause_type == "illegal_termination" and "解除" not in text and "辞退" not in text:
        missing.append("解除或离职的具体时间与方式")
    return missing[:4]


def _official_links(cause_type: str, channel_id: str | None = None) -> list[dict]:
    links = get_guidance_links()
    out = []
    id_order = ["12348", "mohrss", "npc_laws"]
    when_map = {
        "12348": "不确定程序、时效或需要人工咨询时",
        "mohrss": "向劳动监察投诉或了解仲裁入口时",
        "npc_laws": "需要核对法条原文时",
    }
    by_id = {l.get("id"): l for l in links}
    for lid in id_order:
        if lid in by_id:
            out.append({
                "id": lid,
                "title": by_id[lid].get("title", lid),
                "when": when_map.get(lid, ""),
            })
    if channel_id == "female-worker":
        out.insert(1, {
            "id": "women_federation",
            "title": "全国妇联",
            "when": "女职工权益咨询与反映（全国入口）",
        })
        out.insert(2, {
            "id": "union_hotline",
            "title": "工会职工维权 12351",
            "when": "可向用人单位工会或上级工会求助",
        })
    return out


def _finalize_intake_result(
    cause_type: str,
    combined: str,
    *,
    summary: str,
    parties: dict | None = None,
    missing_info: list[str] | None = None,
    recommended_tools: list[dict] | None = None,
    credibility: dict | None = None,
    extracted_from_images: str = "",
) -> dict[str, Any]:
    channel_id = _match_channel(combined)
    scenario_id = _match_scenario(channel_id, combined)
    parties = parties or {}

    checklist_data = get_evidence_checklists().get(cause_type, {})
    checklist = list(checklist_data.get("required") or [])
    doc_prefill = _recommend_docgen_prefill(cause_type, combined, summary)
    doc_type = str(doc_prefill.get("docType") or _DOC_TYPE_MAP.get(cause_type, "application"))
    search_q = f"{_cause_label(cause_type)} 劳动仲裁"

    action_plan = build_action_plan(
        cause_type=cause_type,
        cause_label=_cause_label(cause_type),
        summary=summary,
        combined=combined,
        parties=parties,
        channel_id=channel_id,
        scenario_id=scenario_id,
        checklist=checklist,
        search_query=search_q,
        doc_type=doc_type,
        doc_mode=str(doc_prefill.get("docMode") or "single"),
        bundle_doc_types=list(doc_prefill.get("bundleDocTypes") or []),
        cause_label_fn=_cause_label,
    )
    # 主线推荐工具以 action_plan 为准，避免 LLM 把专区/检索法规混入步骤
    tools = plan_to_recommended_tools(action_plan)
    if not tools:
        tools = _build_tools(cause_type, summary, combined, parties, channel_id, scenario_id)

    cred = credibility or {}

    return {
        "cause_type": cause_type,
        "cause_label": _cause_label(cause_type),
        "summary": summary,
        "parties": {
            "plaintiff": parties.get("plaintiff"),
            "defendant": parties.get("defendant"),
        },
        "missing_info": missing_info or _default_missing(cause_type, combined),
        "evidence_checklist": checklist,
        "recommended_tools": tools,
        "action_plan": action_plan,
        "official_links": _official_links(cause_type, channel_id),
        "channel_id": channel_id,
        "scenario_id": scenario_id,
        "credibility": {
            "score": float(cred.get("score", 0.6)),
            "needs_human_review": bool(cred.get("needs_human_review", True)),
            "reason": cred.get("reason") or "AI 辅助整理，不构成法律意见",
        },
        "extracted_from_images": extracted_from_images[:2000] if extracted_from_images else "",
        "search_query": search_q,
    }


def analyze_with_rules(text: str, image_text: str = "") -> dict[str, Any]:
    combined = "\n".join(filter(None, [text.strip(), image_text.strip()]))
    if not combined:
        combined = "（用户未提供文字描述）"

    cause_type = _match_cause(combined)
    channel_id = _match_channel(combined)
    scenario_id = _match_scenario(channel_id, combined)
    summary = combined[:200] if len(combined) > 200 else combined
    if len(combined) > 200:
        summary = combined[:197] + "..."

    missing = _default_missing(cause_type, combined)
    checklist_data = get_evidence_checklists().get(cause_type, {})
    checklist = list(checklist_data.get("required") or [])

    credibility_score = 0.45 if missing else 0.65
    if image_text.strip():
        credibility_score = min(0.85, credibility_score + 0.15)

    return _finalize_intake_result(
        cause_type,
        combined,
        summary=summary.split("\n")[0][:120],
        missing_info=missing,
        recommended_tools=_build_tools(cause_type, summary, combined, {}, channel_id, scenario_id),
        credibility={
            "score": round(credibility_score, 2),
            "needs_human_review": True,
            "reason": "信息尚不完整，建议补充后人工或官方渠道复核" if missing else "AI 辅助整理，不构成法律意见",
        },
        extracted_from_images=image_text,
    )


_INTake_PROMPT = """你是劳动者维权助手。根据用户描述（及图片 OCR 文字），输出 JSON，不要其他文字。

## 可选案由 ID（cause_type 必须从中选一）
wage_arrears | illegal_termination | overtime_pay | no_written_contract

## 可选 agent_id
cases | evidence | docgen | contract | research | vault

（勿在 recommended_tools 中推荐 channels、search、guidance；专区与检索法规由用户从「专项入口」「其他功能」自行进入。）

## 输出格式
{
  "cause_type": "wage_arrears",
  "summary": "一句话案情摘要（120字内）",
  "parties": {"plaintiff": "劳动者称呼或姓名", "defendant": "公司或老板称呼"},
  "missing_info": ["还缺的信息"],
  "recommended_tools": [
    {"agent_id": "cases", "priority": 1, "reason": "推荐理由", "action": "create_case",
     "prefill": {"title": "...", "case_type": "administrative_labor", "description": "...", "plaintiff": "", "defendant": ""}}
  ],
  "docgen_hint": {"docMode": "single|bundle", "bundleDocTypes": ["application","evidence_list"]},
  "credibility": {"score": 0.7, "needs_human_review": true, "reason": "..."}
}

## 用户描述
{text}

## 图片 OCR 文字
{image_text}
"""


async def analyze_intake(text: str, image_text: str = "", llm=None) -> dict[str, Any]:
    """LLM 结构化分析，失败时回退规则引擎。"""
    combined = "\n".join(filter(None, [text.strip(), image_text.strip()]))
    if not combined.strip():
        raise ValueError("请至少输入文字描述或上传图片")

    if llm is None:
        settings = get_settings()
        if not settings.LLM_API_KEY:
            return analyze_with_rules(text, image_text)
        client = create_llm_client_from_settings(settings)
        llm = type("L", (), {"client": client, "model": settings.LLM_MODEL, "max_tokens": 4096})()

    prompt = (
        _INTake_PROMPT.replace("{text}", text[:8000] or "（无文字）")
        .replace("{image_text}", image_text[:4000] or "（无图片文字）")
    )

    try:
        response = await llm.client.messages.create(
            model=llm.model,
            max_tokens=min(llm.max_tokens, 4096),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
    except Exception as exc:
        logger.warning("Intake LLM failed, using rules: %s", exc)
        return analyze_with_rules(text, image_text)

    cause_type = parsed.get("cause_type") or _match_cause(combined)
    if cause_type not in _CAUSE_KEYWORDS:
        cause_type = _match_cause(combined)

    parties = parsed.get("parties") or {}
    summary = parsed.get("summary") or combined[:120]

    tools = parsed.get("recommended_tools")

    return _finalize_intake_result(
        cause_type,
        combined,
        summary=summary,
        parties=parties,
        missing_info=parsed.get("missing_info"),
        recommended_tools=tools,
        credibility=parsed.get("credibility") or {},
        extracted_from_images=image_text,
    )
