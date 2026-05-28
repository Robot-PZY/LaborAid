"""得理法律开放平台适配器（法规 + 案例）。

对接接口：
- /api/qa/v3/search/queryListLaw
- /api/qa/v3/search/lawInfo
- /api/qa/v3/search/queryListCase
- /api/qa/v3/search/caseInfo
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.data_sources.base import (
    CaseSearchResult,
    DataSourceRegistry,
    LawSearchResult,
    LegalDataSourceAdapter,
)

logger = logging.getLogger(__name__)


def _pick(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return default


class DeliLegalAdapter(LegalDataSourceAdapter):
    name = "delilegal"
    description = "得理法律开放平台"
    supported_types = ["law", "case"]

    def __init__(self, *, base_url: str, appid: str, secret: str):
        self._base_url = (base_url or "https://openapi.delilegal.com").rstrip("/")
        self._appid = (appid or "").strip()
        self._secret = (secret or "").strip()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0))

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "appid": self._appid,
            "secret": self._secret,
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        resp = await self._client.post(url, headers=self._headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {}
        return data

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        resp = await self._client.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {}
        return data

    async def search_law(self, query: str, **filters) -> list[LawSearchResult]:
        if not query.strip():
            return []
        page_size = min(int(filters.get("limit", 10) or 10), 10)
        payload = {
            "pageNo": int(filters.get("pageNo", 1) or 1),
            "pageSize": page_size,
            "sortField": "correlation",
            "sortOrder": "desc",
            "condition": {
                "keywords": [query.strip()],
            },
        }
        try:
            data = await self._post("/api/qa/v3/search/queryListLaw", payload)
            body = data.get("body") if isinstance(data.get("body"), dict) else {}
            rows = body.get("data") if isinstance(body.get("data"), list) else []
            out: list[LawSearchResult] = []
            for row in rows[:page_size]:
                if not isinstance(row, dict):
                    continue
                out.append(
                    LawSearchResult(
                        source=self.description,
                        document_id=_pick(row, "id", "lawId"),
                        title=_pick(row, "title"),
                        provision_ref="",
                        content=(
                            f"效力：{_pick(row, 'timelinessName')}；发布机关：{_pick(row, 'publisherName')}；"
                            f"发布日期：{_pick(row, 'publishDate')}"
                        ),
                        relevance_score=0.78,
                        metadata={
                            "timelinessName": _pick(row, "timelinessName"),
                            "publisherName": _pick(row, "publisherName"),
                            "issuedNo": _pick(row, "issuedNo"),
                            "publishDate": _pick(row, "publishDate"),
                            "activeDate": _pick(row, "activeDate"),
                        },
                    )
                )
            return out
        except Exception as e:
            logger.warning("DeliLegal(得理) search_law failed: %s", e)
            return []

    async def search_case(self, query: str, **filters) -> list[CaseSearchResult]:
        if not query.strip():
            return []
        page_size = min(int(filters.get("limit", 10) or 10), 10)
        payload = {
            "pageNo": int(filters.get("pageNo", 1) or 1),
            "pageSize": page_size,
            "sortField": "correlation",
            "sortOrder": "desc",
            "condition": {
                "keywordArr": [query.strip()],
            },
        }
        try:
            data = await self._post("/api/qa/v3/search/queryListCase", payload)
            body = data.get("body") if isinstance(data.get("body"), dict) else {}
            rows = body.get("data") if isinstance(body.get("data"), list) else []
            out: list[CaseSearchResult] = []
            for row in rows[:page_size]:
                if not isinstance(row, dict):
                    continue
                out.append(
                    CaseSearchResult(
                        source=self.description,
                        case_id=_pick(row, "id"),
                        case_number=_pick(row, "caseNumber", "caseNo"),
                        title=_pick(row, "title", "name", "caseName"),
                        court=_pick(row, "court"),
                        date=_pick(row, "judgementDate", "judgmentDate"),
                        judgment_type=_pick(row, "documentName", "judgmentType"),
                        content=_pick(row, "summary", "courtView", "content"),
                        relevance_score=0.76,
                        metadata={
                            "queryId": _pick(body, "queryId"),
                        },
                    )
                )
            return out
        except Exception as e:
            logger.warning("DeliLegal(得理) search_case failed: %s", e)
            return []

    async def get_provision(self, doc_id: str, article: str | None = None) -> dict | None:
        if not doc_id:
            return None
        try:
            data = await self._get(
                "/api/qa/v3/search/lawInfo",
                {"lawId": doc_id, "merge": "true"},
            )
            body = data.get("body") if isinstance(data.get("body"), dict) else {}
            return body or None
        except Exception as e:
            logger.warning("DeliLegal(得理) get_provision failed: %s", e)
            return None

    async def get_case_detail(self, case_id: str, *, merge: bool = False) -> dict | None:
        if not case_id:
            return None
        try:
            data = await self._get(
                "/api/qa/v3/search/caseInfo",
                {"caseId": case_id, "merge": str(bool(merge)).lower()},
            )
            body = data.get("body") if isinstance(data.get("body"), dict) else {}
            return body or None
        except Exception as e:
            logger.warning("DeliLegal(得理) get_case_detail failed: %s", e)
            return None

    async def health_check(self) -> bool:
        try:
            result = await self.search_law("劳动合同", limit=1)
            return bool(result)
        except Exception:
            return False

    async def aclose(self):
        await self._client.aclose()


def register_delilegal(*, base_url: str, appid: str, secret: str) -> DeliLegalAdapter:
    adapter = DeliLegalAdapter(base_url=base_url, appid=appid, secret=secret)
    DataSourceRegistry.register(adapter)
    logger.info("DeliLegal(得理) adapter registered")
    return adapter

