"""案情分析智能体 — 汇总材料生成阶段报告。"""

from __future__ import annotations

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.helpers import combined_score, prefill_doc
from app.services.agents.routes import alt_step, build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext


class ResearchAgent(CaseAgent):
    agent_id = "research"
    name = "分析案情"
    role = "汇总案件、证据与文书，生成维权阶段总结报告"

    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        case = ctx.case
        score = combined_score(ctx)
        route = build_agent_route(self.agent_id, case.id)

        if ctx.research_reports_count > 0:
            return self._eval(
                status="done",
                summary=f"已有 {ctx.research_reports_count} 份案情分析报告",
                route=route,
                pipeline_stage="research",
            )

        if ctx.documents_count == 0:
            return self._eval(
                status="idle",
                summary="文书生成后可输出更完整的案情报告",
                route=route,
                pipeline_stage="research",
            )

        if score < 40:
            return self._eval(
                status="optional",
                summary="材料完整度偏低，可稍后生成报告",
                route=route,
                pipeline_stage="research",
            )

        explanation = (
            f"已有关联文书 {ctx.documents_count} 份、证据 {ctx.evidence_count} 份。"
            "可生成阶段性案情分析报告，用于复盘与提交前自检。"
        )
        doc_prefill = prefill_doc(ctx)
        next_step = ProposedStep(
            label="生成总结报告",
            reason="材料与文书已具备，适合输出案情分析",
            explanation=explanation,
            pipeline_stage="research",
            alternatives=[
                alt_step("docgen", "继续生成文书", "补充其他类型文书", ctx, doc_prefill),
                alt_step("evidence", "继续补充证据", "提高材料完整度", ctx),
            ],
        )
        return self._eval(
            status="active",
            summary=explanation[:120],
            route=route,
            pipeline_stage="research",
            next_step=next_step,
        )
