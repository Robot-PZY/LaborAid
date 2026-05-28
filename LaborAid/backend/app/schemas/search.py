from pydantic import BaseModel, field_validator


class SearchQuery(BaseModel):
    query: str
    result_type: str = "all"  # law / case / all
    sources: list[str] | None = None
    top_k: int = 20
    case_id: int | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "合同违约赔偿标准",
                    "result_type": "all",
                    "top_k": 20,
                }
            ]
        }
    }

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("搜索内容不能为空")
        if len(v.strip()) > 2000:
            raise ValueError("搜索内容不能超过2000字")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def top_k_range(cls, v):
        if v < 1 or v > 100:
            raise ValueError("top_k 必须在 1-100 之间")
        return v


class LawSearchResult(BaseModel):
    source: str
    document_id: str
    title: str
    provision_ref: str | None = None
    content: str
    relevance_score: float = 0.0
    metadata: dict = {}


class CaseSearchResult(BaseModel):
    source: str
    case_id: str
    case_number: str
    title: str
    court: str
    date: str
    judgment_type: str
    content: str
    relevance_score: float = 0.0
    metadata: dict = {}


class UnifiedSearchResult(BaseModel):
    query: str
    laws: list[LawSearchResult] = []
    cases: list[CaseSearchResult] = []
    total: int = 0
    sources_used: list[str] = []
