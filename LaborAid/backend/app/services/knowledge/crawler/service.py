"""官方法规爬取并写入平台知识库 + 法条向量库。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_on_create
from app.models.knowledge import KnowledgeItem
from app.models.user import User
from app.services.knowledge.crawler.chunker import split_law_articles
from app.services.knowledge.crawler.npc_client import LawDocument, NpcLawClient

logger = logging.getLogger(__name__)

_SEEDS_PATH = Path(__file__).resolve().parents[4] / "data" / "knowledge_crawl_seeds.json"


@dataclass
class CrawlSource:
    id: str
    name: str
    provider: str
    website: str | None = None
    description: str | None = None
    search_keywords: list[str] = field(default_factory=list)
    max_items_per_keyword: int = 6
    tags: list[str] = field(default_factory=list)


@dataclass
class CrawlSeed:
    id: str
    name: str
    keywords: list[str]
    tags: list[str]
    category: str
    source_id: str = "npc_flk"


@dataclass
class CrawlLawResult:
    seed_id: str | None
    keyword: str
    title: str
    source_id: str | None = None
    bbbs: str | None = None
    status: str = "pending"
    knowledge_items: int = 0
    statute_vectors: int = 0
    message: str = ""


@dataclass
class CrawlRunResult:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    items: list[CrawlLawResult] = field(default_factory=list)


class LawCrawlService:
    def __init__(self, client: NpcLawClient | None = None):
        self._client = client or NpcLawClient()

    @staticmethod
    def _load_raw() -> dict:
        if not _SEEDS_PATH.exists():
            return {"sources": [], "seeds": []}
        return json.loads(_SEEDS_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def load_sources() -> list[CrawlSource]:
        raw = LawCrawlService._load_raw()
        return [
            CrawlSource(
                id=s["id"],
                name=s["name"],
                provider=s.get("provider", "npc_flk"),
                website=s.get("website"),
                description=s.get("description"),
                search_keywords=s.get("search_keywords") or [],
                max_items_per_keyword=int(s.get("max_items_per_keyword") or 6),
                tags=s.get("tags") or ["官方法规"],
            )
            for s in raw.get("sources", [])
        ]

    @staticmethod
    def load_seeds() -> list[CrawlSeed]:
        raw = LawCrawlService._load_raw()
        return [
            CrawlSeed(
                id=s["id"],
                name=s["name"],
                keywords=s.get("keywords") or [s["name"]],
                tags=s.get("tags") or ["官方法规"],
                category=s.get("category") or "法律",
                source_id=s.get("source_id") or "npc_flk",
            )
            for s in raw.get("seeds", [])
        ]

    @staticmethod
    def seeds_as_dict() -> dict:
        return LawCrawlService._load_raw()

    async def run(
        self,
        db: AsyncSession,
        user: User,
        *,
        seed_ids: list[str] | None = None,
        keywords: list[str] | None = None,
        source_ids: list[str] | None = None,
        include_statutes: bool = True,
        include_topic_discovery: bool = False,
        dry_run: bool = False,
    ) -> CrawlRunResult:
        seeds = self.load_seeds()
        sources = self.load_sources()
        targets: list[tuple[CrawlSeed | None, str, str | None]] = []
        seen_bbbs: set[str] = set()

        if seed_ids:
            seed_map = {s.id: s for s in seeds}
            for sid in seed_ids:
                seed = seed_map.get(sid)
                if seed:
                    targets.append((seed, seed.keywords[0], seed.source_id))
                else:
                    targets.append((None, sid, "npc_flk"))

        if keywords:
            for kw in keywords:
                targets.append((None, kw.strip(), "npc_flk"))

        if not targets and not include_topic_discovery:
            for s in seeds:
                targets.append((s, s.keywords[0], s.source_id))

        result = CrawlRunResult()

        for seed, keyword, source_id in targets:
            law_result = await self._process_keyword(
                db, user, seed, keyword, source_id or "npc_flk",
                include_statutes=include_statutes,
                dry_run=dry_run,
                seen_bbbs=seen_bbbs,
            )
            result.items.append(law_result)
            if law_result.status == "success":
                result.success += 1
            elif law_result.status == "preview":
                result.success += 1
            elif law_result.status == "skipped":
                result.skipped += 1
            else:
                result.failed += 1

        if include_topic_discovery:
            topic_sources = [s for s in sources if s.provider == "npc_topic"]
            if source_ids:
                topic_sources = [s for s in topic_sources if s.id in source_ids]
            for src in topic_sources:
                topic_items = await self._run_topic_source(
                    db, user, src,
                    include_statutes=include_statutes,
                    dry_run=dry_run,
                    seen_bbbs=seen_bbbs,
                )
                result.items.extend(topic_items)
                for item in topic_items:
                    if item.status in ("success", "preview"):
                        result.success += 1
                    elif item.status == "skipped":
                        result.skipped += 1
                    else:
                        result.failed += 1

        if not dry_run:
            invalidate_on_create("knowledge", "platform")
        return result

    async def _run_topic_source(
        self,
        db: AsyncSession,
        user: User,
        source: CrawlSource,
        *,
        include_statutes: bool,
        dry_run: bool,
        seen_bbbs: set[str],
    ) -> list[CrawlLawResult]:
        items: list[CrawlLawResult] = []
        for kw in source.search_keywords:
            try:
                hits = await self._client.search(kw, page_size=source.max_items_per_keyword, fuzzy=True)
            except Exception as e:
                items.append(CrawlLawResult(
                    seed_id=None,
                    keyword=kw,
                    title=kw,
                    source_id=source.id,
                    status="failed",
                    message=str(e),
                ))
                continue

            for hit in hits:
                if not hit.bbbs or hit.bbbs in seen_bbbs:
                    items.append(CrawlLawResult(
                        seed_id=None,
                        keyword=kw,
                        title=hit.title,
                        source_id=source.id,
                        bbbs=hit.bbbs,
                        status="skipped",
                        message="已同步过，跳过",
                    ))
                    continue

                law_result = CrawlLawResult(
                    seed_id=None,
                    keyword=kw,
                    title=hit.title,
                    source_id=source.id,
                    bbbs=hit.bbbs,
                )
                try:
                    doc = await self._client.fetch_document(hit.bbbs, title_hint=hit.title)
                    seen_bbbs.add(doc.bbbs)
                    law_result.title = doc.title
                    if dry_run:
                        law_result.status = "preview"
                        law_result.message = f"已获取正文 {len(doc.text)} 字"
                    else:
                        tags = list(source.tags)
                        if doc.law_type and doc.law_type not in tags:
                            tags.append(doc.law_type)
                        k_count, s_count = await self._ingest_document(
                            db, user, doc.title, doc.text,
                            source=doc.source_url, tags=tags, bbbs=doc.bbbs,
                            include_statutes=include_statutes,
                            meta={
                                "publish_date": doc.publish_date,
                                "effective_date": doc.effective_date,
                                "authority": doc.authority,
                                "law_type": doc.law_type,
                                "discover_keyword": kw,
                            },
                        )
                        law_result.knowledge_items = k_count
                        law_result.statute_vectors = s_count
                        law_result.status = "success"
                        law_result.message = f"专题发现入库 {k_count} 条"
                except Exception as e:
                    law_result.status = "failed"
                    law_result.message = str(e)
                items.append(law_result)
        return items

    async def _process_keyword(
        self,
        db: AsyncSession,
        user: User,
        seed: CrawlSeed | None,
        keyword: str,
        source_id: str,
        *,
        include_statutes: bool,
        dry_run: bool,
        seen_bbbs: set[str],
    ) -> CrawlLawResult:
        law_result = CrawlLawResult(
            seed_id=seed.id if seed else None,
            keyword=keyword,
            title=seed.name if seed else keyword,
            source_id=source_id,
        )
        try:
            doc = await self._client.fetch_by_keyword(keyword)
            if doc.bbbs in seen_bbbs:
                law_result.title = doc.title
                law_result.bbbs = doc.bbbs
                law_result.status = "skipped"
                law_result.message = "本次任务中已同步，跳过"
                return law_result

            seen_bbbs.add(doc.bbbs)
            law_result.title = doc.title
            law_result.bbbs = doc.bbbs
            if dry_run:
                law_result.status = "preview"
                law_result.message = f"已获取正文 {len(doc.text)} 字"
                return law_result

            tags = list(seed.tags if seed else ["官方法规"])
            if doc.law_type and doc.law_type not in tags:
                tags.append(doc.law_type)
            k_count, s_count = await self._ingest_document(
                db, user, doc.title, doc.text,
                source=doc.source_url, tags=tags, bbbs=doc.bbbs,
                include_statutes=include_statutes,
                meta={
                    "publish_date": doc.publish_date,
                    "effective_date": doc.effective_date,
                    "authority": doc.authority,
                    "law_type": doc.law_type,
                },
            )
            law_result.knowledge_items = k_count
            law_result.statute_vectors = s_count
            law_result.status = "success"
            law_result.message = f"已入库 {k_count} 条知识、{s_count} 条法条向量"
        except Exception as e:
            logger.warning("Crawl failed for %s: %s", keyword, e)
            law_result.status = "failed"
            law_result.message = str(e)
        return law_result

    async def _ingest_document(
        self,
        db: AsyncSession,
        user: User,
        law_name: str,
        text: str,
        *,
        source: str,
        tags: list[str],
        bbbs: str,
        include_statutes: bool,
        meta: dict,
    ) -> tuple[int, int]:
        chunks = split_law_articles(text, law_name)
        knowledge_count = 0
        knowledge_rows: list[KnowledgeItem] = []
        statute_items: list[dict] = []

        for idx, (title, content) in enumerate(chunks):
            row = await self._upsert_knowledge(
                db, user, title=title, content=content[:50000],
                source=source, tags=tags,
            )
            knowledge_count += 1
            knowledge_rows.append(row)

            if include_statutes:
                statute_items.append({
                    "id": f"statute_{bbbs}_{idx}",
                    "title": title,
                    "content": content[:8000],
                    "metadata": {
                        "source": source,
                        "bbbs": bbbs,
                        "law_name": law_name,
                        **{k: str(v) for k, v in meta.items() if v},
                    },
                })

        await self._ingest_knowledge_vectors_batch(db, knowledge_rows)

        statute_count = 0
        if statute_items:
            try:
                from app.services.vector.store import get_vector_service
                svc = get_vector_service()
                statute_count = await svc.add_statutes(statute_items)
            except Exception as e:
                logger.warning("Statute vector ingest failed: %s", e)

        await db.commit()
        return knowledge_count, statute_count

    async def _upsert_knowledge(
        self,
        db: AsyncSession,
        user: User,
        *,
        title: str,
        content: str,
        source: str,
        tags: list[str],
    ) -> KnowledgeItem:
        existing = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.title == title,
                KnowledgeItem.is_platform.is_(True),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.content = content
            row.source = source
            row.tags = tags
            await db.flush()
            await db.refresh(row)
            return row

        row = KnowledgeItem(
            title=title,
            content=content,
            source=source,
            tags=tags,
            is_platform=True,
            owner_id=user.id,
            team_id=None,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def _ingest_knowledge_vectors_batch(self, db: AsyncSession, rows: list[KnowledgeItem]) -> None:
        if not rows:
            return
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()
            payload = [{
                "id": f"knowledge_{row.id}",
                "title": row.title,
                "content": row.content[:5000],
                "metadata": {
                    "source": row.source or "",
                    "type": "knowledge",
                    "tags": ",".join(row.tags or []),
                },
            } for row in rows]
            count = await svc.add_knowledge(payload)
            if count:
                for row in rows:
                    row.embedding_id = f"knowledge_{row.id}"
                await db.flush()
        except Exception as e:
            logger.warning("Batch knowledge vector ingest failed: %s", e)
