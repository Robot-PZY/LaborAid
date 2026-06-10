from datetime import datetime
from pydantic import BaseModel, field_validator


class CaseCreate(BaseModel):
    case_number: str | None = None
    title: str
    case_type: str
    court: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    description: str | None = None
    filing_date: str | None = None
    hearing_dates: list[str] | None = None
    deadline_dates: list[str] | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("案件标题不能为空")
        if len(v.strip()) > 200:
            raise ValueError("案件标题不能超过200字")
        return v.strip()

    @field_validator("case_type")
    @classmethod
    def case_type_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("案件类型不能为空")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_length_limit(cls, v):
        if v and len(v) > 50000:
            raise ValueError("案件描述不能超过50000字")
        return v


class CaseUpdate(BaseModel):
    case_number: str | None = None
    title: str | None = None
    case_type: str | None = None
    court: str | None = None
    status: str | None = None
    plaintiff: str | None = None
    defendant: str | None = None
    description: str | None = None
    filing_date: str | None = None
    hearing_dates: list[str] | None = None
    deadline_dates: list[str] | None = None


class CaseReportRequest(BaseModel):
    extra_notes: str | None = None

    @field_validator("extra_notes")
    @classmethod
    def notes_length(cls, v):
        if v and len(v) > 2000:
            raise ValueError("补充说明不能超过2000字")
        return v.strip() if v else v


class CaseOut(BaseModel):
    id: int
    case_number: str | None
    title: str
    case_type: str
    court: str | None
    status: str
    plaintiff: str | None
    defendant: str | None
    description: str | None
    owner_id: int
    team_id: int | None
    filing_date: str | None
    hearing_dates: list | None
    deadline_dates: list | None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    model_config = {"from_attributes": True}


class CaseDocFactsOut(BaseModel):
    case_facts: str


class CaseDocRecommendationItem(BaseModel):
    doc_type: str
    label: str
    reason: str
    priority: int
    generated: bool = False
    document_id: int | None = None


class CaseDocRecommendationsOut(BaseModel):
    cause_type: str
    cause_label: str
    summary: str
    recommendations: list[CaseDocRecommendationItem]
    case_facts_preview: str | None = None


class CaseReadinessAction(BaseModel):
    label: str
    route: str
    reason: str


class CaseEvidenceSuggestion(BaseModel):
    item: str
    status: str  # missing | covered | optional
    priority: str  # required | optional


class CaseReadinessOut(BaseModel):
    case_id: int
    readiness_score: int
    readiness_level: str
    summary: str
    strengths: list[str]
    missing_items: list[str]
    next_actions: list[CaseReadinessAction]
    cause_type: str | None = None
    cause_label: str | None = None
    evidence_suggestions: list[CaseEvidenceSuggestion] = []
    docgen_ready: bool = False
    docgen_recommendation: str = "not_ready"  # ready | caution | not_ready
    docgen_blockers: list[str] = []
    chain_completeness_score: int | None = None
    combined_score: int | None = None
    intake_checklist: list[str] = []
