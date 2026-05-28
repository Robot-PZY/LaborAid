"""向量检索 Schema"""

import re
from pydantic import BaseModel, field_validator


class VectorIngestItem(BaseModel):
    id: str
    title: str
    content: str
    metadata: dict | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "case_001",
                    "title": "张三诉李四合同纠纷案",
                    "content": "原告张三与被告李四签订借款合同...",
                    "metadata": {"court": "北京市朝阳区人民法院", "year": 2024},
                }
            ]
        }
    }

    @field_validator("id")
    @classmethod
    def id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("条目ID不能为空")
        return v.strip()


class VectorIngestRequest(BaseModel):
    collection: str  # "cases" or "statutes"
    items: list[VectorIngestItem]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "collection": "cases",
                    "items": [
                        {"id": "case_001", "title": "案例标题", "content": "案例内容"},
                    ],
                }
            ]
        }
    }

    @field_validator("collection")
    @classmethod
    def collection_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("集合名称不能为空")
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("集合名称只能包含字母、数字和下划线")
        return v


class VectorSearchQuery(BaseModel):
    query: str
    collection: str = "all"  # "cases", "statutes", "all"
    top_k: int = 10

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "合同违约赔偿",
                    "collection": "all",
                    "top_k": 10,
                }
            ]
        }
    }

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("搜索内容不能为空")
        return v.strip()

    @field_validator("collection")
    @classmethod
    def collection_must_be_alphanumeric(cls, v):
        if v == "all":
            return v
        if not v or not v.strip():
            raise ValueError("集合名称不能为空")
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("集合名称只能包含字母、数字和下划线")
        return v

    @field_validator("top_k")
    @classmethod
    def top_k_range(cls, v):
        if v < 1 or v > 100:
            raise ValueError("top_k 必须在 1-100 之间")
        return v


class VectorSearchResult(BaseModel):
    id: str
    content: str
    metadata: dict
    distance: float


class VectorSearchResponse(BaseModel):
    query: str
    cases: list[VectorSearchResult]
    statutes: list[VectorSearchResult]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "合同违约赔偿",
                    "cases": [],
                    "statutes": [],
                }
            ]
        }
    }


class VectorStats(BaseModel):
    cases_count: int
    statutes_count: int
    knowledge_count: int = 0
    connected: bool

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "cases_count": 150,
                    "statutes_count": 500,
                    "knowledge_count": 80,
                    "connected": True,
                }
            ]
        }
    }
