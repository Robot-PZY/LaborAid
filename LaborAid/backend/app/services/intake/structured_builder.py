"""结构化专项 intake — 表单答案 → 与 analyze 相同的结果结构。"""

from __future__ import annotations

from typing import Any

from app.services.intake.analyzer import (
    _DOC_TYPE_MAP,
    _cause_label,
    _finalize_intake_result,
    _official_links,
    _recommend_docgen_prefill,
)
from app.services.intake.config_loader import (
    get_evidence_checklists,
    get_intake_scenario_meta,
    get_special_channel_scenario,
)


def _scenario_key(channel_id: str, scenario_id: str) -> str:
    return f"{channel_id}:{scenario_id}"


def _validate_answers(
    fields: list[dict],
    answers: dict[str, Any],
) -> list[str]:
    missing: list[str] = []
    for field in fields:
        if not field.get("required"):
            continue
        fid = field.get("id")
        if not fid:
            continue
        val = answers.get(fid)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field.get("label") or fid)
    return missing


def _render_case_facts(
    *,
    channel_title: str,
    scenario_title: str,
    answers: dict[str, Any],
    field_defs: list[dict],
) -> str:
    lines = [
        f"【专项维权】{channel_title} · {scenario_title}",
        "",
    ]
    label_by_id = {f["id"]: f.get("label", f["id"]) for f in field_defs if f.get("id")}
    for fid, label in label_by_id.items():
        val = answers.get(fid)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        lines.append(f"{label}：{val}")
    return "\n".join(lines).strip()


def _extract_parties(answers: dict[str, Any]) -> dict[str, str | None]:
    defendant = (
        answers.get("employer_name")
        or answers.get("subcontractor")
        or answers.get("general_contractor")
    )
    plaintiff = answers.get("plaintiff_name") or answers.get("plaintiff")
    return {
        "plaintiff": str(plaintiff).strip() if plaintiff else None,
        "defendant": str(defendant).strip() if defendant else None,
    }


def _merge_checklist(cause_type: str, scenario_checklist: list[str] | None) -> list[str]:
    if scenario_checklist:
        return list(scenario_checklist)
    data = get_evidence_checklists().get(cause_type, {})
    return list(data.get("required") or [])


def build_structured_intake(
    *,
    channel_id: str,
    scenario_id: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    """规则构建 intake 结果，不调用 LLM。"""
    channel, scenario, meta = get_special_channel_scenario(channel_id, scenario_id)
    if not channel or not scenario:
        raise ValueError("未找到对应的专项场景配置")

    common_fields = list(meta.get("common_fields") or [])
    scenario_fields = list(meta.get("form_fields") or [])
    all_fields = common_fields + scenario_fields

    missing_labels = _validate_answers(all_fields, answers)
    cause_type = meta.get("cause_type") or "wage_arrears"

    case_facts = _render_case_facts(
        channel_title=channel.get("title") or channel_id,
        scenario_title=scenario.get("title") or scenario_id,
        answers=answers,
        field_defs=all_fields,
    )
    summary = case_facts.split("\n")[0][:120]
    if len(case_facts) > 120:
        summary = case_facts[:117] + "..."

    parties = _extract_parties(answers)
    checklist = _merge_checklist(
        cause_type,
        scenario.get("evidence_checklist"),
    )

    doc_prefill = _recommend_docgen_prefill(cause_type, case_facts, summary)
    doc_type = str(doc_prefill.get("docType") or _DOC_TYPE_MAP.get(cause_type, "application"))

    missing_info: list[str] = []
    if missing_labels:
        missing_info.extend([f"请补充：{label}" for label in missing_labels])
    if not parties.get("defendant"):
        missing_info.append("用人单位全称")

    credibility_score = 0.75 if not missing_labels else 0.55

    result = _finalize_intake_result(
        cause_type,
        case_facts,
        summary=summary,
        parties=parties,
        missing_info=missing_info[:6],
        credibility={
            "score": credibility_score,
            "needs_human_review": True,
            "reason": "结构化表单整理，不构成法律意见；关键事实请自行核对",
        },
    )

    # 显式 channel/scenario（_finalize 内 keyword 匹配可能被覆盖）
    result["channel_id"] = channel_id
    result["scenario_id"] = scenario_id
    result["evidence_checklist"] = checklist

    # 用场景 checklist 更新 plan 中 evidence 步骤
    plan = result.get("action_plan") or {}
    for step in plan.get("steps") or []:
        if step.get("step_type") == "evidence":
            prefill = step.get("prefill") or {}
            prefill["checklist"] = checklist
            prefill["channelId"] = channel_id
            prefill["scenarioId"] = scenario_id
            step["prefill"] = prefill
        if step.get("step_type") == "create_case":
            prefill = step.get("prefill") or {}
            prefill["description"] = case_facts
            step["prefill"] = prefill
        if step.get("step_type") == "docgen":
            prefill = step.get("prefill") or {}
            prefill["caseFacts"] = case_facts
            prefill["channelId"] = channel_id
            prefill["scenarioId"] = scenario_id
            step["prefill"] = prefill

    result["action_plan"] = plan
    result["official_links"] = _official_links(cause_type, channel_id)
    result["intake_mode"] = "structured"
    result["structured_answers"] = answers
    result["cause_label"] = _cause_label(cause_type)
    result["case_facts"] = case_facts

    return result
