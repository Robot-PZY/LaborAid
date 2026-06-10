"""案件 AI 就绪度与案由化证据建议。"""

from __future__ import annotations

import re

from app.models.case import Case
from app.models.evidence import Evidence
from app.schemas.case import CaseReadinessAction, CaseReadinessOut, CaseEvidenceSuggestion
from app.services.intake.analyzer import _match_cause, _cause_label
from app.services.intake.config_loader import get_evidence_checklists

# 文书生成推荐阈值
DOCGEN_SCORE_READY = 70       # 综合分 >= 70 → 直接推荐生成
DOCGEN_SCORE_CAUTION = 50     # 综合分 >= 50 → 可生成但带风险提示
# 综合分 < 50 → 不推荐生成

# 清单项 -> 在标题/OCR/案情中匹配的关键词
_CHECKLIST_KEYWORDS: dict[str, list[str]] = {
    "劳动关系证明": ["劳动合同", "劳动", "入职", "工牌", "社保", "工作证", "聘用", "派遣"],
    "工资标准或约定": ["工资", "薪资", "薪酬", "约定", "offer", "底薪"],
    "欠薪期间说明": ["欠薪", "拖欠", "月份", "期间", "未发"],
    "工资银行流水或工资条": ["流水", "银行", "工资条", "转账", "发放"],
    "考勤记录": ["考勤", "打卡", "出勤", "签到"],
    "催要工资的聊天记录": ["催", "聊天", "微信", "讨薪", "要钱"],
    "同事证言": ["同事", "证人", "证言"],
    "解除劳动合同通知或相关沟通记录": ["解除", "辞退", "开除", "通知", "离职", "解雇"],
    "离职时间说明": ["离职", "解除", "最后工作日", "离开"],
    "规章制度": ["规章", "制度", "员工手册"],
    "工作证或工牌": ["工牌", "工作证", "胸牌"],
    "考勤或加班证明": ["考勤", "加班", "打卡", "超时"],
    "工资标准": ["工资", "薪资", "标准"],
    "加班审批记录": ["加班", "审批", "申请"],
    "工作群安排加班的聊天": ["加班", "群", "安排", "微信"],
    "工资条中加班项": ["工资条", "加班"],
    "入职时间证明": ["入职", "到岗", "试用期", "报到"],
    "工资发放记录": ["工资", "流水", "发放", "转账"],
    "社保缴纳记录": ["社保", "五险", "缴纳"],
    "同事或客户证明": ["同事", "客户", "证明", "证言"],
}


def infer_cause_type(case: Case, intake_cause_type: str | None = None) -> str:
    from app.services.intake.case_binding import get_case_intake

    snap_cause = get_case_intake(case).get("cause_type")
    if snap_cause and snap_cause in get_evidence_checklists():
        return snap_cause
    if intake_cause_type and intake_cause_type in get_evidence_checklists():
        return intake_cause_type
    text = "\n".join(
        filter(
            None,
            [case.title or "", case.description or "", case.plaintiff or "", case.defendant or ""],
        )
    )
    return _match_cause(text)


def _evidence_corpus(case: Case, evidences: list[Evidence]) -> str:
    parts = [case.description or "", case.title or ""]
    for ev in evidences:
        parts.append(ev.title or "")
        if ev.ocr_text:
            parts.append((ev.ocr_text or "")[:2000])
        if ev.tags:
            if isinstance(ev.tags, list):
                parts.extend(str(t) for t in ev.tags)
    return "\n".join(parts).lower()


def _item_covered(item: str, corpus: str) -> bool:
    if item.lower() in corpus:
        return True
    keywords = _CHECKLIST_KEYWORDS.get(item, [])
    if not keywords:
        # 回退：取清单项前 4 个字作为弱匹配
        short = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", item)[:4]
        return bool(short and short in corpus)
    hits = sum(1 for kw in keywords if kw in corpus)
    return hits >= max(1, len(keywords) // 2)


def build_evidence_suggestions(
    cause_type: str,
    evidences: list[Evidence],
    case: Case,
) -> list[CaseEvidenceSuggestion]:
    checklist = get_evidence_checklists().get(cause_type, {})
    corpus = _evidence_corpus(case, evidences)
    out: list[CaseEvidenceSuggestion] = []

    for item in checklist.get("required") or []:
        covered = _item_covered(item, corpus)
        out.append(
            CaseEvidenceSuggestion(
                item=item,
                status="covered" if covered else "missing",
                priority="required",
            )
        )
    for item in checklist.get("optional") or []:
        covered = _item_covered(item, corpus)
        out.append(
            CaseEvidenceSuggestion(
                item=item,
                status="covered" if covered else "optional",
                priority="optional",
            )
        )
    return out


def build_evidence_suggestions_from_checklist(
    items: list[str],
    evidences: list[Evidence],
    case: Case,
) -> list[CaseEvidenceSuggestion]:
    if not items:
        return []
    corpus = _evidence_corpus(case, evidences)
    return [
        CaseEvidenceSuggestion(
            item=item,
            status="covered" if _item_covered(item, corpus) else "missing",
            priority="required",
        )
        for item in items
    ]


def build_case_readiness(
    case: Case,
    *,
    documents_count: int,
    evidence_count: int,
    evidence_with_ocr_count: int,
    evidences: list[Evidence] | None = None,
    intake_cause_type: str | None = None,
    intake_checklist: list[str] | None = None,
    chain_completeness_score: int | None = None,
) -> CaseReadinessOut:
    evidences = evidences or []
    cause_type = infer_cause_type(case, intake_cause_type)
    cause_label = _cause_label(cause_type)
    checklist_data = get_evidence_checklists().get(cause_type, {})
    tips = checklist_data.get("tips") or ""

    score = 0
    strengths: list[str] = []
    missing_items: list[str] = []
    actions: list[CaseReadinessAction] = []

    custom_checklist = [x for x in (intake_checklist or []) if x]
    if custom_checklist:
        suggestions = build_evidence_suggestions_from_checklist(custom_checklist, evidences, case)
    else:
        suggestions = build_evidence_suggestions(cause_type, evidences, case)
    required_missing = [s.item for s in suggestions if s.priority == "required" and s.status == "missing"]

    if (case.description or "").strip():
        score += 20
        strengths.append("已填写案件描述")
    else:
        missing_items.append("补充案件经过与争议焦点（时间、金额、主体）")

    if (case.plaintiff or "").strip() and (case.defendant or "").strip():
        score += 10
        strengths.append("当事人信息较完整")
    else:
        missing_items.append("补充申请人/被申请人（或原告/被告）全称")

    if evidence_count > 0:
        score += 15
        strengths.append(f"已上传 {evidence_count} 份证据")
    else:
        missing_items.append("至少上传 1 份关键证据")

    if evidence_with_ocr_count > 0:
        score += 10
        strengths.append("已有可检索 OCR 文本")
    elif evidence_count > 0:
        missing_items.append("建议上传更清晰扫描件以便 OCR 提取")

    covered_required = sum(
        1 for s in suggestions if s.priority == "required" and s.status == "covered"
    )
    total_required = sum(1 for s in suggestions if s.priority == "required")
    if total_required > 0:
        ratio = covered_required / total_required
        score += int(25 * ratio)
        if ratio >= 0.75:
            strengths.append(f"关键证据项已覆盖 {covered_required}/{total_required}")
        elif required_missing:
            for item in required_missing[:3]:
                missing_items.append(f"建议补充：{item}")

    if documents_count > 0:
        score += 10
        strengths.append(f"已生成 {documents_count} 份文书")
    else:
        missing_items.append("可生成仲裁申请书或证据清单草稿")

    docgen_blockers: list[str] = []
    if not (case.description or "").strip() and not _has_evidence_text(evidences):
        docgen_blockers.append("缺少案情描述，文书事实部分可能过于空泛")
    if evidence_count == 0:
        docgen_blockers.append("尚无证据材料，建议先上传工资流水、合同或沟通记录")
    if required_missing:
        docgen_blockers.append(f"仍缺 {len(required_missing)} 项关键证据：{required_missing[0]}")

    if not actions and evidence_count == 0:
        actions.append(
            CaseReadinessAction(
                label="上传证据材料",
                route=f"/evidence?caseId={case.id}",
                reason="按案由补齐关键证据可显著提升 AI 输出质量",
            )
        )
    elif required_missing:
        actions.append(
            CaseReadinessAction(
                label="补齐关键证据",
                route=f"/evidence?caseId={case.id}",
                reason=f"当前案由「{cause_label}」仍缺：{required_missing[0]}",
            )
        )

    if not (case.description or "").strip():
        actions.append(
            CaseReadinessAction(
                label="完善案件信息",
                route=f"/cases?open={case.id}",
                reason="完善案情描述有助于文书与报告生成",
            )
        )

    if score >= 50:
        actions.append(
            CaseReadinessAction(
                label="生成总结报告",
                route=f"/research?caseId={case.id}",
                reason="可输出阶段性维权分析报告",
            )
        )

    if tips and readiness_level != "high":
        missing_items.append(tips)

    # 去重保序
    seen: set[str] = set()
    deduped_missing: list[str] = []
    for m in missing_items:
        if m not in seen:
            seen.add(m)
            deduped_missing.append(m)

    readiness_score = max(0, min(100, score))
    chain_score: int | None = None
    combined_score = readiness_score
    if chain_completeness_score is not None:
        chain_score = max(0, min(100, int(chain_completeness_score)))
        combined_score = max(
            0,
            min(100, round(readiness_score * 0.65 + chain_score * 0.35)),
        )
        if chain_score < 50 and readiness_score >= 50:
            deduped_missing.insert(
                0,
                f"证据链完整度 {chain_score} 分偏低，建议按时间线补强关键证据",
            )
        elif chain_score >= 70 and readiness_score < 70:
            strengths.append(f"证据链分析 {chain_score} 分，链条较完整")

    # 综合分等级
    if combined_score >= 70:
        readiness_level = "high"
    elif combined_score >= 45:
        readiness_level = "medium"
    else:
        readiness_level = "low"

    # 三档文书生成推荐
    has_description = bool((case.description or "").strip())
    has_evidence_text = _has_evidence_text(evidences)
    hard_block = evidence_count == 0 or (not has_description and not has_evidence_text)

    if hard_block or combined_score < DOCGEN_SCORE_CAUTION:
        docgen_recommendation = "not_ready"
    elif combined_score >= DOCGEN_SCORE_READY:
        docgen_recommendation = "ready"
    else:
        docgen_recommendation = "caution"

    docgen_ready = docgen_recommendation in ("ready", "caution")

    # 按档位生成 summary
    if docgen_recommendation == "ready":
        summary = f"「{cause_label}」材料充分（综合 {combined_score} 分），可生成文书。"
    elif docgen_recommendation == "caution":
        summary = f"「{cause_label}」基础已具备（综合 {combined_score} 分），建议先补齐关键证据再定稿。"
    else:
        summary = f"「{cause_label}」材料不足（综合 {combined_score} 分），请先补充描述与核心证据。"

    # 按档位生成文书 action
    if documents_count == 0:
        if docgen_recommendation == "ready":
            actions.append(
                CaseReadinessAction(
                    label="生成维权文书",
                    route="/documents?worker=1",
                    reason="材料充分，可直接生成申请书或证据清单",
                )
            )
        elif docgen_recommendation == "caution":
            actions.append(
                CaseReadinessAction(
                    label="生成维权文书（材料不完整）",
                    route="/documents?worker=1",
                    reason="综合分未达 70，生成文书可能不够完整",
                )
            )

    return CaseReadinessOut(
        case_id=case.id,
        readiness_score=readiness_score,
        readiness_level=readiness_level,
        summary=summary,
        strengths=strengths[:6],
        missing_items=deduped_missing[:8],
        next_actions=actions[:5],
        cause_type=cause_type,
        cause_label=cause_label,
        evidence_suggestions=suggestions,
        docgen_ready=docgen_ready,
        docgen_recommendation=docgen_recommendation,
        docgen_blockers=docgen_blockers[:4],
        chain_completeness_score=chain_score,
        combined_score=combined_score,
        intake_checklist=custom_checklist,
    )


def _has_evidence_text(evidences: list[Evidence]) -> bool:
    return any((e.ocr_text or "").strip() for e in evidences)
