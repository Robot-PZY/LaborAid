"""自定义API数据源适配器 — 配置驱动，无需写代码"""

import logging

import httpx
import yaml
from pathlib import Path

from app.config import PROJECT_ROOT
from app.services.data_sources.base import (
    LegalDataSourceAdapter,
    LawSearchResult,
    CaseSearchResult,
    DataSourceRegistry,
)

logger = logging.getLogger(__name__)


class CustomAPIAdapter(LegalDataSourceAdapter):
    """通过YAML配置文件接入任意第三方法律API"""

    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.name = self.config.get("name", "custom")
        self.description = self.config.get("display_name", "自定义API")
        self.supported_types = self.config.get("supported_types", ["law", "case"])
        self.base_url = self.config.get("base_url", "")
        self._client = httpx.AsyncClient(timeout=30)

    def _get_headers(self) -> dict:
        auth = self.config.get("auth", {})
        if auth.get("type") == "bearer":
            return {"Authorization": f"Bearer {auth.get('token', '')}"}
        elif auth.get("type") == "api_key":
            key_name = auth.get("header_name", "X-API-Key")
            return {key_name: auth.get("api_key", "")}
        return {}

    async def _call_endpoint(self, endpoint_name: str, **params) -> list[dict]:
        endpoint = self.config.get("endpoints", {}).get(endpoint_name)
        if not endpoint:
            return []

        url = self.base_url + endpoint["path"]
        for k, v in params.items():
            url = url.replace(f"{{{k}}}", str(v))

        method = endpoint.get("method", "GET").upper()
        resp = await self._client.request(
            method, url, headers=self._get_headers(),
            json={"query": params.get("query", "")} if method == "POST" else None,
            params={"query": params.get("query", "")} if method == "GET" else None,
        )
        resp.raise_for_status()
        return resp.json()

    async def search_law(self, query: str, **filters) -> list[LawSearchResult]:
        try:
            raw = await self._call_endpoint("search_law", query=query, **filters)
            mapping = self.config["endpoints"]["search_law"].get("response_mapping", {})
            results = []
            for item in raw:
                results.append(LawSearchResult(
                    source=self.description,
                    document_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    content=item.get("full_text", ""),
                ))
            return results
        except Exception as e:
            logger.warning("Custom API search_law failed [%s]: %s", self.description, e)
            return []

    async def search_case(self, query: str, **filters) -> list[CaseSearchResult]:
        try:
            raw = await self._call_endpoint("search_case", query=query, **filters)
            results = []
            for item in raw:
                results.append(CaseSearchResult(
                    source=self.description,
                    case_id=str(item.get("id", "")),
                    case_number=item.get("case_no", ""),
                    title=item.get("name", ""),
                    court=item.get("court_name", ""),
                    date=item.get("judgment_date", ""),
                    content=item.get("summary", ""),
                ))
            return results
        except Exception as e:
            logger.warning("Custom API search_case failed [%s]: %s", self.description, e)
            return []

    async def get_provision(self, doc_id: str, article: str = None) -> dict | None:
        try:
            raw = await self._call_endpoint("get_provision", doc_id=doc_id, article=article)
            return raw if isinstance(raw, dict) else None
        except Exception as e:
            logger.warning("Custom API get_provision failed [%s]: %s", self.description, e)
            return None

    async def health_check(self) -> bool:
        try:
            hc = self.config.get("health_check")
            if not hc:
                return True
            url = self.base_url + hc["path"]
            resp = await self._client.get(url, headers=self._get_headers())
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Custom API health_check failed [%s]: %s", self.description, e)
            return False

    async def aclose(self):
        """Clean up the HTTP client."""
        await self._client.aclose()


def load_custom_data_sources(config_dir: str | Path | None = None):
    """从配置目录加载所有自定义数据源（默认：项目根 config/data_sources）。"""
    if config_dir is None:
        config_path = PROJECT_ROOT / "config" / "data_sources"
    else:
        config_path = Path(config_dir)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path
    if not config_path.exists():
        return

    for f in config_path.glob("*.yml"):
        try:
            adapter = CustomAPIAdapter(str(f))
            DataSourceRegistry.register(adapter)
        except Exception as e:
            logger.warning("Failed to load custom data source %s: %s", f, e)
