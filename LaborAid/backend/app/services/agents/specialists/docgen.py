"""文书生成智能体 — 起草申请书、证据清单等。"""

from __future__ import annotations

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.helpers import (
    cause_label,
    combined_score,
    common_blockers,
    prefill_doc,
    required_missing,
)
from app.services.agents.routes import alt_step, build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext


class DocgenAgent(CaseAgent):
    agent_id = "docgen"
    name = "生成文书"
    role = "基于案情与证据 AI 起草仲裁申请书、证据清单等文书"

    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        case = ctx.case
        r = ctx.readiness
        score = combined_score(ctx)
        blockers = common_blockers(ctx)
        doc_prefill = prefill_doc(ctx)
        route = build_agent_route(self.agent_id, case.id, doc_prefill)

        if ctx.documents_count > 0:
            return self._eval(
                status="done",
                summary=f"已生成 {ctx.documents_count} 份关联文书",
                route=route,
                pipeline_stage="documents",
            )

        if ctx.evidence_count == 0 or required_missing(ctx):
            return self._eval(
                status="blocked",
                summary="需先由证据智能体补齐关键材料",
                blockers=blockers,
                route=route,
                pipeline_stage="documents",
            )

        if not r.docgen_ready:
            return self._eval(
                status="blocked",
                summary="材料完整度不足，暂不满足文书生成条件",
                blockers=r.docgen_blockers or blockers,
                route=route,
                pipeline_stage="documents",
            )

        cause_lbl = cause_label(ctx)
        explanation = (
            f"「{cause_lbl}」材料完整度约 {score}%，可生成仲裁申请书、证据清单等文书，"
            "生成后请人工核对事实与请求事项。"
        )
        alts = [alt_step("research", "先做案情分析", "汇总现有材料形成阶段报告", ctx)]
        if any(kw in (case.description or "") for kw in ["合同", "协议"]):
            alts.insert(0, alt_step("contract", "审查合同", "识别解除与报酬条款风险", ctx))

        next_step = ProposedStep(
            label="生成维权文书",
            reason="材料基础已具备，可起草申请书或证据清单",
            explanation=explanation,
            pipeline_stage="documents",
            blockers=blockers,
            prefill=doc_prefill,
            alternatives=alts,
        )
        return self._eval(
            status="active",
            summary=explanation[:120],
            blockers=blockers,
            route=route,
            pipeline_stage="documents",
            next_step=next_step,
        )
