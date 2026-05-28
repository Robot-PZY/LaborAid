"""维权计划生成 — 规则驱动分步路径（默认先建案，欠薪类监察/线索优先于文书）。"""

from __future__ import annotations

from datetime import date
from typing import Any


def _case_title_with_date(label: str) -> str:
    """案件标题前缀：2026.5.27 拖欠工资维权"""
    today = date.today()
    return f"{today.year}.{today.month}.{today.day} {label}"


def _cause_label(cause_type: str, label_fn) -> str:
    return label_fn(cause_type)


def build_action_plan(
    *,
    cause_type: str,
    cause_label: str,
    summary: str,
    combined: str,
    parties: dict,
    channel_id: str | None,
    scenario_id: str | None,
    checklist: list[str],
    search_query: str,
    doc_type: str,
    doc_mode: str = "single",
    bundle_doc_types: list[str] | None = None,
    cause_label_fn,
) -> dict[str, Any]:
    """生成有序维权计划。步骤 1 固定为建案。"""
    text = combined or summary or ""
    steps: list[dict[str, Any]] = []
    n = 0

    def add(
        step_type: str,
        label: str,
        reason: str,
        *,
        agent_id: str | None = None,
        action: str = "navigate",
        prefill: dict | None = None,
        platform_category: str | None = None,
        optional: bool = False,
    ) -> None:
        nonlocal n
        n += 1
        steps.append({
            "step": n,
            "step_type": step_type,
            "label": label,
            "reason": reason,
            "agent_id": agent_id,
            "action": action,
            "prefill": prefill or {},
            "platform_category": platform_category,
            "official_link_id": platform_category,
            "optional": optional,
        })

    title = cause_label or _cause_label(cause_type, cause_label_fn)
    plan_id = cause_type
    if channel_id:
        plan_id = f"{plan_id}_{channel_id}"
    if scenario_id:
        plan_id = f"{plan_id}_{scenario_id}"

    # 1. 建案（用户确认：默认必须先建立案件）
    add(
        "create_case",
        "建立案件档案",
        "先归档案情，后续证据与文书都挂在同一案件下，便于导出材料包",
        agent_id="cases",
        action="create_case",
        prefill={
            "title": _case_title_with_date(f"{title}维权"),
            "case_type": "administrative_labor",
            "description": summary or text[:500],
            "plaintiff": parties.get("plaintiff"),
            "defendant": parties.get("defendant"),
        },
    )

    # 专区匹配仅通过 channel_id 返回前端「专项入口」卡片展示，不纳入主线步骤。

    # 2. 欠薪类：监察/线索举报优先于文书（用户确认）
    wants_report = any(
        kw in text
        for kw in ["举报", "监察", "投诉", "12333", "人社", "欠薪线索"]
    )
    if cause_type == "wage_arrears" and (
        channel_id == "migrant-worker" or wants_report or any(k in text for k in ["包工头", "工地", "农民工"])
    ):
        platform = "wage_clue" if channel_id == "migrant-worker" else "labor_inspection"
        add(
            "official_external",
            "向有关部门反映欠薪",
            "工程建设领域欠薪可优先通过国务院客户端线索反映；亦可向属地劳动监察投诉",
            action="external",
            platform_category=platform,
        )

    if channel_id == "female-worker" and any(k in text for k in ["怀孕", "产假", "三期", "生育", "哺乳"]):
        add(
            "official_external",
            "妇联 / 工会维权咨询",
            "女职工权益问题可咨询妇联或工会职工维权热线",
            action="external",
            platform_category="women_federation",
            optional=True,
        )

    # 4. 整理证据
    add(
        "evidence",
        "上传并整理证据",
        "按清单准备工资条、流水、聊天截图、考勤等材料",
        agent_id="evidence",
        prefill={"checklist": checklist},
    )

    # 5. 合同（若提及）
    if any(kw in text for kw in ["合同", "协议", "劳动合同", "实习协议"]):
        add(
            "contract",
            "审查相关合同",
            "识别解除、报酬、试用期等风险条款",
            agent_id="contract",
            optional=True,
        )

    # 6. 生成文书
    add(
        "docgen",
        "生成仲裁申请书等材料",
        "在证据整理后生成申请书、证据清单等文书",
        agent_id="docgen",
        prefill={
            "docType": doc_type,
            "docMode": doc_mode,
            "bundleDocTypes": bundle_doc_types or [],
            "caseFacts": summary or text[:800],
        },
    )

    # 7. 案情分析（主线收尾，可选）
    add(
        "research",
        "分析案情并生成报告",
        "汇总案件、证据与文书，形成阶段维权分析与建议",
        agent_id="research",
        optional=True,
    )

    plan_title = f"您的维权安排：{title}"
    if cause_type == "wage_arrears":
        plan_title = "您的维权安排：登记案件、整理证据、按需投诉、准备文书"

    return {
        "plan_id": plan_id,
        "title": plan_title,
        "steps": steps,
        "current_step": 1,
    }


def plan_to_recommended_tools(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """兼容旧版 recommended_tools 字段。"""
    out: list[dict[str, Any]] = []
    for s in plan.get("steps") or []:
        agent_id = s.get("agent_id")
        if not agent_id and s.get("step_type") != "official_external":
            continue
        if s.get("step_type") == "official_external":
            continue
        out.append({
            "agent_id": agent_id,
            "priority": s.get("step", len(out) + 1),
            "reason": s.get("reason", ""),
            "action": s.get("action", "navigate"),
            "prefill": s.get("prefill") or {},
        })
    return out
