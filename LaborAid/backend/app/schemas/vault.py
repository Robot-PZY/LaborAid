from datetime import datetime

from pydantic import BaseModel, Field


class UserMaterialOut(BaseModel):
    id: int
    user_id: int
    case_id: int | None
    source: str
    source_id: int | None
    title: str
    original_filename: str
    mime_type: str | None
    size_bytes: int
    stage: str
    tags: list[str] | None
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserMaterialUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    stage: str | None = None
    case_id: int | None = None
    tags: list[str] | None = None
    note: str | None = None


class VaultStatsOut(BaseModel):
    total_files: int
    total_bytes: int
    quota_bytes: int
    by_stage: dict[str, int]


class VaultBulkDeleteIn(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)


class VaultBulkDeleteOut(BaseModel):
    deleted: int
