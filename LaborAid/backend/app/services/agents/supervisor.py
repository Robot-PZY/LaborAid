"""调度智能体 — 聚合各协作智能体评估并决定下一步。"""

from __future__ import annotations

from typing import Any

from app.services.agents.base import AgentEvaluation, ProposedStep
from app.services.agents.routes import build_agent_route
from app.services.agents.specialists import PIPELINE_AGENTS
from app.services.orchestrator.case_context import CaseWorkContext, context_to_api_dict


def evaluate_all_agents(ctx: CaseWorkContext) -> list[AgentEvaluation]:
    return [agent.evaluate(ctx) for agent in PIPELINE_AGENTS]


def _pick_next_proposal(evaluations: list[AgentEvaluation]) -> tuple[str, ProposedStep] | None:
    for ev in evaluations:
        if ev.next_step is not None:
            return ev.agent_id, ev.next_step
    return None


def _pack_next_step(
    ctx: CaseWorkContext,
    *,
    agent_id: str,
    proposal: ProposedStep,
) -> dict[str, Any]:
    from app.services.orchestrator.pipeline_tasks import build_pipeline_tasks

    from app.services.workflow import workflow_stage_from_pipeline

    return {
        "case_id": ctx.case.id,
        "agent_id": agent_id,
        "action": "navigate",
        "label": proposal.label,
        "route": build_agent_route(agent_id, ctx.case.id, proposal.prefill),
        "reason": proposal.reason,
        "explanation": proposal.explanation,
        "pipeline_stage": proposal.pipeline_stage,
        "workflow_stage": workflow_stage_from_pipeline(proposal.pipeline_stage),
        "blockers": proposal.blockers[:6],
        "prefill": proposal.prefill,
        "context": context_to_api_dict(ctx),
        "alternatives": proposal.alternatives[:3],
        "pipeline_tasks": build_pipeline_tasks(ctx, proposal.pipeline_stage),
    }


def compute_case_next_step(ctx: CaseWorkContext) -> dict[str, Any]:
    """Supervisor 入口：与原有 next-step API 兼容。"""
    evaluations = evaluate_all_agents(ctx)
    picked = _pick_next_proposal(evaluations)
    if not picked:
        # 兜底：回首页
        return _pack_next_step(
            ctx,
            agent_id="hub",
            proposal=ProposedStep(
                label="返回服务首页",
                reason="暂无明确下一步",
                explanation="请从首页继续选择工具。",
                pipeline_stage="complete",
            ),
        )
    agent_id, proposal = picked
    return _pack_next_step(ctx, agent_id=agent_id, proposal=proposal)


def build_agents_list_payload(ctx: CaseWorkContext) -> dict[str, Any]:
    evaluations = evaluate_all_agents(ctx)
    picked = _pick_next_proposal(evaluations)
    active_id = picked[0] if picked else None
    handoffs: list[dict[str, str]] = []

    prev_active: str | None = None
    for ev in evaluations:
        if ev.status == "active" and ev.agent_id != active_id:
            if prev_active and prev_active != ev.agent_id:
                handoffs.append(
                    {
                        "from_agent": prev_active,
                        "to_agent": ev.agent_id,
                        "reason": ev.summary[:80],
                    }
                )
            prev_active = ev.agent_id

    return {
        "case_id": ctx.case.id,
        "active_agent_id": active_id,
        "agents": [ev.to_api_dict() for ev in evaluations],
        "handoffs": handoffs,
        "supervisor_summary": _supervisor_summary(evaluations, active_id),
    }


def _supervisor_summary(evaluations: list[AgentEvaluation], active_id: str | None) -> str:
    if not active_id:
        return "各智能体暂无紧急待办，可按需使用工具。"
    active = next((e for e in evaluations if e.agent_id == active_id), None)
    if active and active.next_step:
        return active.next_step.explanation
    if active:
        return active.summary
    return "调度中…"
