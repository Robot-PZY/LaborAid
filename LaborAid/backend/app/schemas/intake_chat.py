"""对话式 intake — 请求/响应模型。"""

from pydantic import BaseModel, Field


class ChatOption(BaseModel):
    """选项卡片"""
    id: str
    label: str
    icon: str = ""
    value: str = ""


class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str  # 'user' | 'assistant'
    content: str
    attachments: list[str] = Field(default_factory=list)


class ChatTurnRequest(BaseModel):
    """单轮对话请求"""
    session_id: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    user_message: str = ""
    attachments: list[str] = Field(default_factory=list)
    selected_option: str | None = None


class AgentStepResult(BaseModel):
    """智能体调度步骤"""
    agent_id: str
    agent_name: str
    action: str
    status: str = "done"
    result_summary: str = ""
    duration_ms: int = 0


class OrchestrationResult(BaseModel):
    """智能体调度结果"""
    steps: list[AgentStepResult] = Field(default_factory=list)
    total_duration_ms: int = 0
    tools_triggered: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    """工具调用结果"""
    tool_id: str
    tool_name: str
    result: dict = Field(default_factory=dict)


class ChatTurnResponse(BaseModel):
    """单轮对话响应"""
    session_id: str
    reply: str
    stage: str = "identity"  # identity | dispute | facts | evidence | analyzing | done
    options: list[ChatOption] = Field(default_factory=list)
    analysis: dict | None = None
    orchestration: OrchestrationResult | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    case_id: int | None = None
    extracted_facts: dict = Field(default_factory=dict)
