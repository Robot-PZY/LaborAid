"""外部数据源统一适配器基类 — 支持任意第三方API接入"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class LawSearchResult(BaseModel):
    source: str
    document_id: str
    title: str
    provision_ref: Optional[str] = None
    content: str
    relevance_score: float = 0.0
    metadata: dict = {}


class CaseSearchResult(BaseModel):
    source: str
    case_id: str
    case_number: str
    title: str
    court: str = ""
    date: str = ""
    judgment_type: str = ""
    content: str
    relevance_score: float = 0.0
    metadata: dict = {}


class LegalDataSourceAdapter(ABC):
    """所有外部法律数据源的基类"""
    name: str = ""
    description: str = ""
    supported_types: list[str] = []

    @abstractmethod
    async def search_law(self, query: str, **filters) -> list[LawSearchResult]:
        ...

    @abstractmethod
    async def search_case(self, query: str, **filters) -> list[CaseSearchResult]:
        ...

    @abstractmethod
    async def get_provision(self, doc_id: str, article: str = None) -> dict | None:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class DataSourceRegistry:
    """数据源注册中心 — 插件式管理"""
    _adapters: dict[str, LegalDataSourceAdapter] = {}

    @classmethod
    def register(cls, adapter: LegalDataSourceAdapter):
        cls._adapters[adapter.name] = adapter

    @classmethod
    def get(cls, name: str) -> Optional[LegalDataSourceAdapter]:
        return cls._adapters.get(name)

    @classmethod
    def get_all(cls) -> dict:
        return cls._adapters.copy()

    @classmethod
    def unregister(cls, name: str):
        cls._adapters.pop(name, None)
