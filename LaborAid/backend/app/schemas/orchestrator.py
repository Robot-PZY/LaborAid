"""案件维权编排 Agent — API 模型。"""

from pydantic import BaseModel, Field, field_validator


class CaseAgentContextOut(BaseModel):
    case_id: int
    cause_type: str | None = None
    cause_label: str | None = None
    channel_id: str | None = None
    documents_count: int = 0
    evidence_count: int = 0
    research_reports_count: int = 0
    has_intake_plan: bool = False
    readiness_score: int = 0
    combined_score: int | None = None


class CaseAgentPipelineTask(BaseModel):
    id: str
    label: str
    status: str  # pending | active | done
    route: str
    hint: str | None = None
    optional: bool = False


class CaseAgentNextStepOut(BaseModel):
    case_id: int
    agent_id: str
    action: str = "navigate"
    label: str
    route: str
    reason: str
    explanation: str
    pipeline_stage: str
    workflow_stage: str = ""
    blockers: list[str] = Field(default_factory=list)
    prefill: dict = Field(default_factory=dict)
    context: CaseAgentContextOut
    alternatives: list[dict] = Field(default_factory=list)
    pipeline_tasks: list[CaseAgentPipelineTask] = Field(default_factory=list)
    disclaimer: str = "本建议由系统自动编排，不构成法律意见；关键决策请以官方渠道或专业人士意见为准。"


class CaseAgentAskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("问题不能为空")
        return s


class CaseAgentSnapshotOut(BaseModel):
    case_id: int
    snapshot: dict = Field(default_factory=dict)


class CaseDocPipelineIn(BaseModel):
    doc_type: str = "application"
    case_facts: str = Field(..., min_length=10, max_length=50000)
    extra_instructions: str | None = Field(None, max_length=4000)
    skip_research: bool = False
    research_report_ids: list[int] | None = None

    @field_validator("case_facts")
    @classmethod
    def strip_facts(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 10:
            raise ValueError("案情描述至少 10 字")
        return s


class CaseAgentAskOut(BaseModel):
    case_id: int
    answer: str
    suggested_route: str
    suggested_label: str
    pipeline_stage: str
    used_llm: bool = False
    disclaimer: str = "本回答仅供参考，不构成法律意见；投诉、立案请以政府部门规定为准。"


class CaseAgentStatusItem(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str  # done | active | blocked | idle | optional
    summary: str
    tool_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    route: str = ""
    pipeline_stage: str | None = None
    suggested_label: str | None = None
    suggested_reason: str | None = None


class CaseAgentHandoff(BaseModel):
    from_agent: str
    to_agent: str
    reason: str


class CaseAgentsListOut(BaseModel):
    case_id: int
    active_agent_id: str | None = None
    agents: list[CaseAgentStatusItem]
    handoffs: list[CaseAgentHandoff] = Field(default_factory=list)
    supervisor_summary: str = ""


class CaseWorkflowStepOut(BaseModel):
    id: str
    label: str
    hint: str
    status: str  # done | active | pending
    route: str
    agent_id: str | None = None


class CaseWorkflowOut(BaseModel):
    case_id: int
    current_stage: str
    progress: int = 0
    total_steps: int = 4
    steps: list[CaseWorkflowStepOut]
    summary: str = ""
    ai_hint: str | None = None
    active_agent_id: str | None = None
