"""协作智能体 ↔ 功能模块映射。

导航里的「功能」在 agents.ts 注册；协作智能体按维权阶段分组，
一个智能体可调度多个功能，并非一功能一 Agent。
"""

from __future__ import annotations

# agent_id -> frontend agents.ts 中的 tool id 列表
AGENT_TOOL_IDS: dict[str, list[str]] = {
    "guidance": ["guidance", "channels", "limitation_calc"],
    "evidence": ["evidence", "vault", "cases"],
    "docgen": ["docgen", "templates"],
    "research": ["research", "search"],
    "records": ["records", "cases", "enterprise", "compensation_calc"],
}


def tool_ids_for_agent(agent_id: str) -> list[str]:
    return list(AGENT_TOOL_IDS.get(agent_id, []))
