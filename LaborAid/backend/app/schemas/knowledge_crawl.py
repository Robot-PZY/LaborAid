"""官方法规爬虫 Schema"""

from pydantic import BaseModel, Field


class CrawlSourceOut(BaseModel):
    id: str
    name: str
    provider: str
    website: str | None = None
    description: str | None = None
    search_keywords: list[str] = Field(default_factory=list)
    max_items_per_keyword: int | None = None


class CrawlSeedOut(BaseModel):
    id: str
    name: str
    keywords: list[str]
    tags: list[str]
    category: str
    source_id: str = "npc_flk"


class CrawlSeedsResponse(BaseModel):
    description: str | None = None
    sources: list[CrawlSourceOut]
    seeds: list[CrawlSeedOut]


class CrawlRunRequest(BaseModel):
    seed_ids: list[str] | None = Field(None, description="预置种子 ID")
    keywords: list[str] | None = Field(None, description="自定义检索关键词（法规全称）")
    source_ids: list[str] | None = Field(None, description="数据源 ID，如 npc_labor_discover")
    include_statutes: bool = Field(True, description="是否同步写入法条向量库")
    include_topic_discovery: bool = Field(False, description="是否执行专题发现（自动扩充相关法规）")
    dry_run: bool = Field(False, description="仅预览抓取结果，不写入数据库")


class CrawlLawResultOut(BaseModel):
    seed_id: str | None = None
    keyword: str
    title: str
    source_id: str | None = None
    bbbs: str | None = None
    status: str
    knowledge_items: int = 0
    statute_vectors: int = 0
    message: str = ""


class CrawlRunResponse(BaseModel):
    total: int
    success: int
    failed: int
    skipped: int = 0
    items: list[CrawlLawResultOut]


class CrawlScheduleStatus(BaseModel):
    enabled: bool
    weekday: int
    hour: int
    minute: int
    last_run_at: str | None = None
    last_run_status: str | None = None
    last_run_summary: dict | None = None
    next_run_at: str | None = None
    running: bool = False


class CrawlScheduleUpdate(BaseModel):
    enabled: bool
