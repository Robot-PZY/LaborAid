"""LangGraph Supervisor 状态机 — 维权流程智能调度。

使用 LangGraph 构建有向图，Supervisor 节点负责调度决策，
专家节点复用现有 CaseAgent.evaluate() 逻辑。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.agents.base import AgentEvaluation, CaseAgent, ProposedStep
from app.services.agents.specialists import PIPELINE_AGENTS
from app.services.orchestrator.case_context import CaseWorkContext, context_to_api_dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class SupervisorState(TypedDict):
    """LangGraph 状态定义。"""

    # 输入
    case_context: CaseWorkContext

    # 中间状态
    evaluations: list[dict]  # AgentEvaluation 序列化后的列表
    active_agent_id: str | None
    next_step: dict | None  # ProposedStep 序列化后的字典

    # 输出
    result: dict | None


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

def supervisor_node(state: SupervisorState) -> dict:
    """Supervisor 节点：评估所有专家 Agent，选择下一步。

    当前使用规则驱动（按优先级顺序），未来可扩展为 LLM 智能调度。
    """
    ctx = state["case_context"]

    # 评估所有专家 Agent
    evaluations: list[AgentEvaluation] = [
        agent.evaluate(ctx) for agent in PIPELINE_AGENTS
    ]

    # 选择第一个有 next_step 的 Agent
    picked: tuple[str, ProposedStep] | None = None
    for ev in evaluations:
        if ev.next_step is not None:
            picked = (ev.agent_id, ev.next_step)
            break

    # 序列化评估结果
    eval_dicts = [ev.to_api_dict() for ev in evaluations]

    if not picked:
        # 没有待办，返回完成状态
        return {
            "evaluations": eval_dicts,
            "active_agent_id": None,
            "next_step": None,
            "result": _build_result(ctx, None, None, eval_dicts),
        }

    agent_id, proposal = picked
    return {
        "evaluations": eval_dicts,
        "active_agent_id": agent_id,
        "next_step": _proposal_to_dict(proposal),
        "result": _build_result(ctx, agent_id, proposal, eval_dicts),
    }


def specialist_node(state: SupervisorState) -> dict:
    """专家节点：透传状态，实际逻辑已在 supervisor 中完成。

    此节点保留用于未来扩展：当需要 LLM 智能调度时，
    可在此处调用 LLM 分析上下文并决定路由。
    """
    return {}


def _proposal_to_dict(proposal: ProposedStep) -> dict:
    """将 ProposedStep 序列化为字典。"""
    return {
        "label": proposal.label,
        "reason": proposal.reason,
        "explanation": proposal.explanation,
        "pipeline_stage": proposal.pipeline_stage,
        "blockers": proposal.blockers[:6],
        "prefill": proposal.prefill,
        "alternatives": proposal.alternatives[:3],
    }


def _build_result(
    ctx: CaseWorkContext,
    agent_id: str | None,
    proposal: ProposedStep | None,
    evaluations: list[dict],
) -> dict:
    """构建最终输出结果，与现有 API 兼容。"""
    from app.services.agents.routes import build_agent_route
    from app.services.orchestrator.pipeline_tasks import build_pipeline_tasks
    from app.services.workflow import workflow_stage_from_pipeline

    if not agent_id or not proposal:
        # 兜底：返回首页
        return {
            "case_id": ctx.case.id,
            "agent_id": "hub",
            "action": "navigate",
            "label": "返回服务首页",
            "route": "/hub",
            "reason": "暂无明确下一步",
            "explanation": "请从首页继续选择工具。",
            "pipeline_stage": "complete",
            "workflow_stage": workflow_stage_from_pipeline("complete"),
            "blockers": [],
            "prefill": {},
            "context": context_to_api_dict(ctx),
            "alternatives": [],
            "pipeline_tasks": [],
        }

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


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def build_supervisor_graph() -> StateGraph:
    """构建 Supervisor LangGraph 状态机。

    图结构：
        START → supervisor → END

    当前为简单线性图，未来可扩展：
    - 添加条件边实现动态路由
    - 添加专家节点实现多轮交互
    - 添加 LLM 决策节点实现智能调度
    """
    graph = StateGraph(SupervisorState)

    # 添加节点
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("specialist", specialist_node)

    # 添加边
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", END)
    graph.add_edge("specialist", END)

    return graph


# 编译图（延迟编译，避免导入时依赖未就绪）
_compiled_graph = None


def get_compiled_graph():
    """获取编译后的 LangGraph 图。"""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_supervisor_graph().compile()
    return _compiled_graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_supervisor(ctx: CaseWorkContext) -> dict:
    """运行 Supervisor 状态机，返回下一步建议。

    这是对外暴露的主入口，与现有 supervisor.compute_case_next_step() 功能等价。
    """
    graph = get_compiled_graph()

    # 初始状态
    initial_state: SupervisorState = {
        "case_context": ctx,
        "evaluations": [],
        "active_agent_id": None,
        "next_step": None,
        "result": None,
    }

    # 运行图
    final_state = graph.invoke(initial_state)

    # 返回结果
    return final_state.get("result") or _build_result(ctx, None, None, [])


def get_agent_evaluations(ctx: CaseWorkContext) -> list[dict]:
    """获取所有 Agent 的评估结果（用于 agents 列表 API）。"""
    graph = get_compiled_graph()

    initial_state: SupervisorState = {
        "case_context": ctx,
        "evaluations": [],
        "active_agent_id": None,
        "next_step": None,
        "result": None,
    }

    final_state = graph.invoke(initial_state)
    return final_state.get("evaluations", [])


def get_graph_structure() -> dict:
    """获取图结构信息（用于可视化）。"""
    return {
        "nodes": ["START", "supervisor", "specialist", "END"],
        "edges": [
            {"from": "START", "to": "supervisor"},
            {"from": "supervisor", "to": "END"},
            {"from": "specialist", "to": "END"},
        ],
        "description": "Supervisor 状态机：START → supervisor → END",
    }
