from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UserRecentItem(BaseModel):
    id: int
    kind: Literal["case", "document", "evidence", "research", "contract"]
    title: str
    updated_at: datetime


class UserOverview(BaseModel):
    cases: int
    documents: int
    evidence: int
    research: int
    contracts: int = 0
    vault_files: int = 0
    vault_bytes: int = 0
    recent: list[UserRecentItem]
