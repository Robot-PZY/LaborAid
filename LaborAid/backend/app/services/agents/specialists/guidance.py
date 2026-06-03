"""维权指引智能体 — 明确案由与办事路径。"""

from __future__ import annotations

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.helpers import cause_type, common_blockers
from app.services.agents.routes import alt_step, build_agent_route
from app.services.orchestrator.case_context import CaseWorkContext


class GuidanceAgent(CaseAgent):
    agent_id = "guidance"
    name = "维权指引"
    role = "按案由梳理维权步骤，链接官方办事与援助渠道"

    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        case = ctx.case
        cause = cause_type(ctx)
        desc_len = len((case.description or "").strip())
        needs_path = not ctx.has_intake_plan and desc_len < 30 and ctx.evidence_count == 0

        if needs_path:
            blockers = common_blockers(ctx)
            explanation = (
                f"案件「{case.title}」材料尚少，建议先通过维权指引明确案由与可走渠道，"
                "再回来补充证据与文书。"
            )
            next_step = ProposedStep(
                label="明确维权路径",
                reason="案情描述较短，先按案由查看步骤与官方渠道",
                explanation=explanation,
                pipeline_stage="path",
                blockers=blockers,
                prefill={"cause": cause},
                alternatives=[
                    alt_step("cases", "完善案件信息", "补充时间、金额与争议焦点", ctx),
                ],
            )
            return self._eval(
                status="active",
                summary="案情尚空，需先明确维权路径与案由",
                blockers=blockers,
                route=build_agent_route(self.agent_id, case.id, {"cause": cause}),
                pipeline_stage="path",
                next_step=next_step,
            )

        status = "done" if ctx.has_intake_plan or desc_len >= 30 else "idle"
        return self._eval(
            status=status,
            summary="维权路径与案由已基本明确" if status == "done" else "可按需回看指引步骤",
            route=build_agent_route(self.agent_id, case.id, {"cause": cause}),
            pipeline_stage="path" if status != "done" else None,
        )
