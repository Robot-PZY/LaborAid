"""证据整理智能体 — 上传、OCR 与证据链分析。"""

from __future__ import annotations

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.helpers import (
    cause_label,
    common_blockers,
    prefill_doc,
    required_missing,
)
from app.services.agents.routes import alt_step, build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext


class EvidenceAgent(CaseAgent):
    agent_id = "evidence"
    name = "整理证据"
    role = "上传证据材料、OCR 识别与证据链完整性分析"

    def _needs_evidence_work(self, ctx: CaseWorkContext) -> bool:
        return ctx.evidence_count == 0 or bool(required_missing(ctx))

    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        case = ctx.case
        r = ctx.readiness
        missing = required_missing(ctx)
        blockers = common_blockers(ctx)
        route = build_agent_route(self.agent_id, case.id)

        if self._needs_evidence_work(ctx):
            first_miss = missing[0] if missing else "关键证据"
            cause_lbl = cause_label(ctx)
            explanation = (
                f"当前为「{cause_lbl}」案由。"
                + (
                    f"建议优先上传：{first_miss}。"
                    if missing
                    else "尚未上传证据，请先整理工资条、合同或沟通记录。"
                )
            )
            alts = []
            if not (case.description or "").strip():
                alts.append(alt_step("cases", "完善案情描述", "便于 OCR 与文书引用事实", ctx))
            if r.docgen_recommendation == "caution":
                alts.append(
                    alt_step(
                        "docgen",
                        "先生成文书草稿",
                        "综合分 50-70，可先起草再补证，但文书可能不够完整",
                        ctx,
                        prefill_doc(ctx),
                    )
                )
            next_step = ProposedStep(
                label="整理证据链",
                reason=f"证据{'未上传' if ctx.evidence_count == 0 else f'仍缺：{first_miss}'}",
                explanation=explanation,
                pipeline_stage="evidence",
                blockers=blockers,
                prefill={
                    "checklist": [
                        s.item
                        for s in (r.evidence_suggestions or [])
                        if s.status == "missing"
                    ][:6],
                },
                alternatives=alts,
            )
            return self._eval(
                status="active",
                summary=explanation[:120],
                blockers=blockers,
                route=route,
                pipeline_stage="evidence",
                next_step=next_step,
            )

        if ctx.documents_count == 0 and r.docgen_recommendation == "not_ready":
            alts = [alt_step("cases", "完善案件信息", "补充案情描述", ctx)]
            next_step = ProposedStep(
                label="补齐后再生成文书",
                reason="文书生成条件尚未满足",
                explanation=(
                    f"综合评分不足，请先补齐：{'；'.join(r.docgen_blockers[:2]) or '案情与核心证据'}，"
                    "再进入文书生成。"
                ),
                pipeline_stage="evidence",
                blockers=r.docgen_blockers or blockers,
                alternatives=alts,
            )
            return self._eval(
                status="blocked",
                summary="证据基础已有，但尚未达到文书生成门槛",
                blockers=r.docgen_blockers or blockers,
                route=route,
                pipeline_stage="evidence",
                next_step=next_step,
            )

        return self._eval(
            status="done",
            summary=f"已上传 {ctx.evidence_count} 份证据，关键项已覆盖",
            route=route,
            pipeline_stage="evidence",
        )
