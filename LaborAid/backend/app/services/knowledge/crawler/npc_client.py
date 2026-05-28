"""全国人大法律法规库 (flk.npc.gov.cn) HTTP 客户端。"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.services.evidence.ocr import extract_text

logger = logging.getLogger(__name__)

_BASE = "https://flk.npc.gov.cn"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://flk.npc.gov.cn/fl.html",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}
_REQUEST_DELAY = 0.6


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


@dataclass
class LawSearchHit:
    bbbs: str
    title: str
    publish_date: str | None
    effective_date: str | None
    authority: str | None
    law_type: str | None


@dataclass
class LawDocument:
    bbbs: str
    title: str
    publish_date: str | None
    effective_date: str | None
    authority: str | None
    law_type: str | None
    source_url: str
    text: str


class NpcLawClient:
    """访问 flk.npc.gov.cn 新版 /law-search/ API。"""

    def __init__(self, request_delay: float = _REQUEST_DELAY):
        self._delay = request_delay

    async def search(self, keyword: str, *, page_size: int = 5, fuzzy: bool = False) -> list[LawSearchHit]:
        payload = {
            "searchContent": keyword,
            "searchRange": 1,
            "searchType": 2 if fuzzy else 1,
            "pageNum": 1,
            "pageSize": page_size,
        }
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30.0) as client:
            resp = await client.post(f"{_BASE}/law-search/search/list", json=payload)
            resp.raise_for_status()
            data = resp.json()
        rows = data.get("rows") or []
        hits: list[LawSearchHit] = []
        for row in rows:
            hits.append(
                LawSearchHit(
                    bbbs=row.get("bbbs", ""),
                    title=_strip_html(row.get("title", "")),
                    publish_date=row.get("gbrq"),
                    effective_date=row.get("sxrq"),
                    authority=row.get("zdjgName"),
                    law_type=row.get("flxz"),
                )
            )
        await asyncio.sleep(self._delay)
        return hits

    async def fetch_document(self, bbbs: str, *, title_hint: str = "") -> LawDocument:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=120.0) as client:
            detail_resp = await client.get(
                f"{_BASE}/law-search/search/flfgDetails",
                params={"bbbs": bbbs},
            )
            detail_resp.raise_for_status()
            detail = detail_resp.json().get("data") or {}

            download_resp = await client.get(
                f"{_BASE}/law-search/download/pc",
                params={"bbbs": bbbs, "format": "docx"},
            )
            download_resp.raise_for_status()
            download_data = download_resp.json().get("data") or {}
            file_url = download_data.get("url")
            if not file_url:
                raise ValueError(f"无法获取法规文件下载链接: {title_hint or bbbs}")

            file_resp = await client.get(file_url)
            file_resp.raise_for_status()

        title = detail.get("title") or title_hint or bbbs
        tmp_dir = Path(tempfile.gettempdir()) / "laboraid_crawl"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{uuid.uuid4().hex[:12]}.docx"
        try:
            tmp_path.write_bytes(file_resp.content)
            text = await extract_text(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        if not text or text.startswith("["):
            raise ValueError(f"法规正文提取失败: {title}")

        await asyncio.sleep(self._delay)
        return LawDocument(
            bbbs=bbbs,
            title=title.strip(),
            publish_date=detail.get("gbrq"),
            effective_date=detail.get("sxrq"),
            authority=detail.get("zdjgName"),
            law_type=detail.get("flxz"),
            source_url=f"https://flk.npc.gov.cn/detail.html?bbbs={bbbs}",
            text=text.strip(),
        )

    async def fetch_by_keyword(self, keyword: str) -> LawDocument:
        hits = await self.search(keyword)
        if not hits:
            raise ValueError(f"未找到法规: {keyword}")
        # 优先标题完全匹配
        chosen = hits[0]
        for hit in hits:
            if hit.title == keyword or keyword in hit.title:
                chosen = hit
                break
        return await self.fetch_document(chosen.bbbs, title_hint=chosen.title)
