"""智能体基类与通用数据结构。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.services.orchestrator.case_context import CaseWorkContext

# done=已完成 | active=当前主责 | blocked=被前置条件卡住 | idle=尚未轮到 | optional=可选项
AgentStatus = str


@dataclass
class ProposedStep:
    """该智能体主张的「下一步」。"""

    label: str
    reason: str
    explanation: str
    pipeline_stage: str
    blockers: list[str] = field(default_factory=list)
    prefill: dict = field(default_factory=dict)
    alternatives: list[dict] = field(default_factory=list)


@dataclass
class AgentEvaluation:
    """单个智能体对当前案件的状态评估。"""

    agent_id: str
    name: str
    role: str
    status: AgentStatus
    summary: str
    tool_ids: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    route: str = ""
    pipeline_stage: str | None = None
    next_step: ProposedStep | None = None

    def to_api_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "summary": self.summary,
            "tool_ids": self.tool_ids,
            "blockers": self.blockers[:6],
            "route": self.route,
            "pipeline_stage": self.pipeline_stage,
        }
        if self.next_step:
            out["suggested_label"] = self.next_step.label
            out["suggested_reason"] = self.next_step.reason
        return out


class CaseAgent(ABC):
    """案件维权协作智能体（可覆盖多个功能模块）。"""

    agent_id: str
    name: str
    role: str

    @abstractmethod
    def evaluate(self, ctx: CaseWorkContext) -> AgentEvaluation:
        """评估当前状态，并可选择是否主张下一步。"""

    def _tools(self) -> list[str]:
        from app.services.agents.capabilities import tool_ids_for_agent

        return tool_ids_for_agent(self.agent_id)

    def _eval(self, **kwargs) -> AgentEvaluation:
        kwargs.setdefault("tool_ids", self._tools())
        kwargs.setdefault("agent_id", self.agent_id)
        kwargs.setdefault("name", self.name)
        kwargs.setdefault("role", self.role)
        return AgentEvaluation(**kwargs)
