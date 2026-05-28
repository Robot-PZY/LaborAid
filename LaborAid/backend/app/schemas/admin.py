"""管理端 API 模型"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class AdminStatsOverview(BaseModel):
    users_total: int
    users_active: int
    users_new_7d: int
    cases_total: int
    documents_total: int
    evidence_total: int
    research_total: int
    llm_configured: bool
    vision_llm_configured: bool


class AdminUserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class AdminUsageByDay(BaseModel):
    date: str
    cases: int = 0
    documents: int = 0
    evidence: int = 0
    research: int = 0
