from datetime import datetime

from pydantic import BaseModel, Field


class IntakeParties(BaseModel):
    plaintiff: str | None = None
    defendant: str | None = None


class IntakeCredibility(BaseModel):
    score: float = Field(ge=0, le=1, default=0.5)
    needs_human_review: bool = True
    reason: str = ""


class IntakeToolPrefill(BaseModel):
    title: str | None = None
    case_type: str | None = None
    description: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    caseFacts: str | None = None
    docType: str | None = None
    docMode: str | None = None
    bundleDocTypes: list[str] = Field(default_factory=list)
    searchQuery: str | None = None
    checklist: list[str] = Field(default_factory=list)
    channelId: str | None = None
    scenarioId: str | None = None


class IntakeRecommendedTool(BaseModel):
    agent_id: str
    priority: int
    reason: str
    action: str = "navigate"
    prefill: IntakeToolPrefill = Field(default_factory=IntakeToolPrefill)


class IntakeOfficialLink(BaseModel):
    id: str
    title: str
    when: str = ""


class IntakePlanStep(BaseModel):
    step: int
    step_type: str
    label: str
    reason: str
    agent_id: str | None = None
    action: str = "navigate"
    prefill: IntakeToolPrefill = Field(default_factory=IntakeToolPrefill)
    platform_category: str | None = None
    official_link_id: str | None = None
    optional: bool = False


class IntakeActionPlan(BaseModel):
    plan_id: str
    title: str
    steps: list[IntakePlanStep] = Field(default_factory=list)
    current_step: int = 1


class IntakeAnalyzeResponse(BaseModel):
    cause_type: str
    cause_label: str
    summary: str
    case_facts: str | None = None
    parties: IntakeParties = Field(default_factory=IntakeParties)
    missing_info: list[str] = Field(default_factory=list)
    evidence_checklist: list[str] = Field(default_factory=list)
    recommended_tools: list[IntakeRecommendedTool] = Field(default_factory=list)
    official_links: list[IntakeOfficialLink] = Field(default_factory=list)
    credibility: IntakeCredibility = Field(default_factory=IntakeCredibility)
    extracted_from_images: str = ""
    search_query: str = ""
    channel_id: str | None = None
    scenario_id: str | None = None
    action_plan: IntakeActionPlan | None = None
    intake_mode: str | None = None
    structured_answers: dict | None = None


class IntakeStructuredRequest(BaseModel):
    channel_id: str
    scenario_id: str
    answers: dict = Field(default_factory=dict)


class IntakeCreateCaseRequest(BaseModel):
    title: str
    case_type: str = "administrative_labor"
    description: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    cause_type: str | None = None


class IntakeSessionSaveRequest(BaseModel):
    """与前端 IntakeSession 一致的 JSON（camelCase）。"""

    session: dict


class IntakeSessionStoredOut(BaseModel):
    session: dict
    updated_at: datetime
