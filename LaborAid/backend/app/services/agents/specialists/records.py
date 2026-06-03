"""记录汇总智能体 — 维权材料归档与导出。"""

from __future__ import annotations

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.helpers import combined_score
from app.services.agents.routes import alt_step, build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext


class RecordsAgent(CaseAgent):
    agent_id = "records"
    name = "我的记录"
    role = "汇总案件、文书、证据与研究记录，支持导出与复盘"

    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        case = ctx.case
        score = combined_score(ctx)
        route = build_agent_route(self.agent_id, case.id)

        main_done = (
            ctx.evidence_count > 0
            and ctx.documents_count > 0
            and (ctx.research_reports_count > 0 or score < 40)
        )

        if not main_done:
            return self._eval(
                status="idle",
                summary="主要维权步骤完成后，可在此统一查看记录",
                route=route,
                pipeline_stage="complete",
            )

        explanation = (
            f"「{case.title}」主要维权步骤已基本完成（完整度 {score}%）。"
            "可查看记录、导出材料包，或按需补充证据与更新报告。"
        )
        next_step = ProposedStep(
            label="查看维权记录",
            reason="本案件阶段性材料已较完整",
            explanation=explanation,
            pipeline_stage="complete",
            alternatives=[
                alt_step("evidence", "补充证据", "进一步提高完整度", ctx),
                alt_step("research", "更新案情报告", "材料有变时可重新分析", ctx),
            ],
        )
        return self._eval(
            status="done",
            summary=explanation[:120],
            route=route,
            pipeline_stage="complete",
            next_step=next_step,
        )
