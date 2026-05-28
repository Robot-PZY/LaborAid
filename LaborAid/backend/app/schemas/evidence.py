"""证据管理 Schema"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator

OcrStatusType = Literal["pending", "processing", "success", "failed"]


EVIDENCE_TYPES = ["documentary", "physical", "electronic", "testimony", "audio_visual", "expert"]


class EvidenceCreate(BaseModel):
    case_id: int
    type: str
    title: str
    tags: list[str] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_id": 1,
                    "type": "documentary",
                    "title": "借款合同原件",
                    "tags": ["合同", "核心证据"],
                }
            ]
        }
    }

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v):
        if v not in EVIDENCE_TYPES:
            raise ValueError(f"证据类型必须是: {', '.join(EVIDENCE_TYPES)}")
        return v

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("证据标题不能为空")
        return v.strip()


class EvidenceUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    sort_order: int | None = None
    analysis: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"title": "更新后的标题", "sort_order": 1}
            ]
        }
    }


class EvidenceOut(BaseModel):
    id: int
    case_id: int
    type: str
    title: str
    file_path: str | None = None
    ocr_text: str | None = None
    tags: list[str] | None = None
    sort_order: int = 0
    analysis: str | None = None
    has_file: bool = False
    ocr_status: OcrStatusType = "pending"
    ocr_message: str | None = None
    vault_archived: bool | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "case_id": 1,
                    "type": "documentary",
                    "title": "借款合同原件",
                    "file_path": None,
                    "ocr_text": None,
                    "tags": ["合同", "核心证据"],
                    "sort_order": 0,
                    "analysis": None,
                    "has_file": False,
                    "created_at": "2026-01-15T10:30:00Z",
                }
            ]
        },
    }
