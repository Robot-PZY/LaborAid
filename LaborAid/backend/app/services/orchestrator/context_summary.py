"""将案件工作区上下文压缩为 LLM 可读摘要。"""

from __future__ import annotations

from app.services.orchestrator.case_context import CaseWorkContext


def build_case_context_text(ctx: CaseWorkContext) -> str:
    case = ctx.case
    r = ctx.readiness
    lines = [
        f"案件标题：{case.title}",
        f"案由：{r.cause_label or '未识别'}（{r.cause_type or '未知'}）",
        f"材料完整度：{r.combined_score if r.combined_score is not None else r.readiness_score}%",
        f"证据 {ctx.evidence_count} 份，文书 {ctx.documents_count} 份，案情报告 {ctx.research_reports_count} 份",
    ]
    if case.description:
        desc = (case.description or "").strip()
        lines.append(f"案情摘要：{desc[:600]}{'…' if len(desc) > 600 else ''}")
    if case.plaintiff or case.defendant:
        lines.append(f"当事人：申请人/原告 {case.plaintiff or '—'}；被申请人/被告 {case.defendant or '—'}")
    if ctx.channel_id:
        lines.append(f"专项通道：{ctx.channel_id}")
    if r.missing_items:
        lines.append("待补项：" + "；".join(r.missing_items[:5]))
    if r.docgen_blockers:
        lines.append("文书阻塞：" + "；".join(r.docgen_blockers[:3]))
    required_miss = [
        s.item for s in (r.evidence_suggestions or []) if s.priority == "required" and s.status == "missing"
    ]
    if required_miss:
        lines.append("缺证据：" + "、".join(required_miss[:5]))
    return "\n".join(lines)
