"""法律研究 Schema"""

from datetime import datetime
from pydantic import BaseModel, field_validator


class ResearchRequest(BaseModel):
    query: str
    sources: list[str] = ["vector_db", "ai_knowledge"]
    case_id: int | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "民间借贷利率上限及违约金标准",
                    "sources": ["vector_db", "ai_knowledge"],
                    "case_id": None,
                }
            ]
        }
    }

    @field_validator("query")
    @classmethod
    def query_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("研究问题不能为空")
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("研究问题不能超过2000个字符")
        return v

    @field_validator("sources")
    @classmethod
    def sources_must_be_valid(cls, v):
        if not v:
            raise ValueError("数据来源列表不能为空")
        valid_sources = {"vector_db", "ai_knowledge", "external_api"}
        for s in v:
            if s not in valid_sources:
                raise ValueError(f"不支持的数据来源: {s}，可选值: {', '.join(sorted(valid_sources))}")
        return v


class ResearchReportOut(BaseModel):
    id: int
    query: str
    report: str
    sources_used: list[str]
    case_id: int | None = None
    created_at: datetime
    conclusion_level: str | None = None

    model_config = {"from_attributes": True}


class ResearchExport(BaseModel):
    format: str = "docx"  # docx / markdown

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"format": "docx"}
            ]
        }
    }
