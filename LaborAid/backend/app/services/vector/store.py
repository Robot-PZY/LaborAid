"""Vector store service -- ChromaDB-backed vector search for cases, statutes,
and knowledge items.

Hardened with connection retry, mid-request unavailability handling, and
collection stats caching.
"""

import asyncio
import logging
import time
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_vector_service = None

# Retry settings for ChromaDB connection
_CONNECT_MAX_RETRIES = 3
_CONNECT_BACKOFF_BASE = 1.0  # seconds

# Stats cache TTL
_STATS_CACHE_TTL = 5.0  # seconds


def get_vector_service() -> "VectorStoreService":
    global _vector_service
    if _vector_service is None:
        settings = get_settings()
        _vector_service = VectorStoreService(settings)
    return _vector_service


class VectorStoreService:

    def __init__(self, settings=None):
        if settings is None:
            settings = get_settings()
        self._settings = settings
        self._client = None
        self._cases_col = None
        self._statutes_col = None
        self._knowledge_col = None
        # Stats cache: (timestamp, stats_dict)
        self._stats_cache: tuple[float, dict] | None = None

    # ── Connection management ────────────────────────────────────────────

    def _ensure_connection(self) -> bool:
        """Ensure ChromaDB is connected.  Uses retry with exponential backoff.

        Note: This is a synchronous method. Callers should wrap it with
        ``asyncio.to_thread()`` to avoid blocking the event loop.
        """
        if self._client is not None:
            return True

        for attempt in range(_CONNECT_MAX_RETRIES):
            try:
                import chromadb
                # Try HTTP client first (remote ChromaDB server)
                try:
                    self._client = chromadb.HttpClient(
                        host=self._settings.CHROMA_HOST,
                        port=self._settings.CHROMA_PORT,
                    )
                    self._client.heartbeat()
                except Exception:
                    # Fallback to embedded PersistentClient for local dev
                    from pathlib import Path
                    db_path = Path(self._settings.UPLOAD_DIR).parent / "chroma_data"
                    db_path.mkdir(parents=True, exist_ok=True)
                    self._client = chromadb.PersistentClient(path=str(db_path))
                self._cases_col = self._client.get_or_create_collection(
                    "legal_cases",
                    metadata={"hnsw:space": "cosine", "description": "法律案例向量库"},
                )
                self._statutes_col = self._client.get_or_create_collection(
                    "legal_statutes",
                    metadata={"hnsw:space": "cosine", "description": "法律法规向量库"},
                )
                self._knowledge_col = self._client.get_or_create_collection(
                    "knowledge",
                    metadata={"hnsw:space": "cosine", "description": "个人知识库"},
                )
                logger.info(
                    "ChromaDB connected (attempt %d), cases=%d, statutes=%d",
                    attempt + 1,
                    self._cases_col.count(),
                    self._statutes_col.count(),
                )
                # Invalidate stats cache on reconnection
                self._stats_cache = None
                return True
            except Exception as e:
                wait = min(_CONNECT_BACKOFF_BASE * (2 ** attempt), 10.0)
                logger.warning(
                    "ChromaDB connection attempt %d/%d failed: %s, retrying in %.1fs",
                    attempt + 1,
                    _CONNECT_MAX_RETRIES,
                    e,
                    wait,
                )
                # Reset client so next attempt starts fresh
                self._client = None
                if attempt < _CONNECT_MAX_RETRIES - 1:
                    import time as _t
                    _t.sleep(wait)

        logger.error("ChromaDB connection failed after %d retries", _CONNECT_MAX_RETRIES)
        self._client = None
        return False

    def _invalidate_connection(self) -> None:
        """Mark the connection as lost so next call retries."""
        logger.warning("ChromaDB connection invalidated -- will retry on next operation")
        self._client = None
        self._cases_col = None
        self._statutes_col = None
        self._knowledge_col = None
        self._stats_cache = None

    # ── Add ───────────────────────────────────────────────────────────────

    async def add_cases(self, items: list[dict]) -> int:
        """Batch-add cases."""
        if not await asyncio.to_thread(self._ensure_connection) or not items:
            return 0
        ids = [str(it["id"]) for it in items]
        docs = [f"{it['title']}\n{it['content']}" for it in items]
        metas = [it.get("metadata", {}) for it in items]
        try:
            await asyncio.to_thread(self._cases_col.upsert, ids=ids, documents=docs, metadatas=metas)
            self._stats_cache = None  # invalidate
            return len(ids)
        except Exception as e:
            logger.error("Add cases failed: %s", e)
            self._invalidate_connection()
            return 0

    async def add_statutes(self, items: list[dict]) -> int:
        """Batch-add statutes."""
        if not await asyncio.to_thread(self._ensure_connection) or not items:
            return 0
        ids = [str(it["id"]) for it in items]
        docs = [f"{it['title']}\n{it['content']}" for it in items]
        metas = [it.get("metadata", {}) for it in items]
        try:
            await asyncio.to_thread(self._statutes_col.upsert, ids=ids, documents=docs, metadatas=metas)
            self._stats_cache = None
            return len(ids)
        except Exception as e:
            logger.error("Add statutes failed: %s", e)
            self._invalidate_connection()
            return 0

    # ── Search ────────────────────────────────────────────────────────────

    async def search_cases(self, query: str, top_k: int = 10, collection: str | None = None) -> list[dict]:
        if not query or not query.strip():
            return []
        if not await asyncio.to_thread(self._ensure_connection):
            return []
        if collection == "knowledge" and self._knowledge_col is not None:
            return await self.search_knowledge(query, top_k)
        try:
            count = self._cases_col.count()
            if not count:
                return []
            results = await asyncio.to_thread(
                self._cases_col.query, query_texts=[query], n_results=min(top_k, count)
            )
            return self._parse_query_results(results)
        except Exception as e:
            logger.warning("Search cases failed: %s", e)
            self._invalidate_connection()
            return []

    async def search_statutes(self, query: str, top_k: int = 10) -> list[dict]:
        if not query or not query.strip():
            return []
        if not await asyncio.to_thread(self._ensure_connection):
            return []
        try:
            count = self._statutes_col.count()
            if not count:
                return []
            results = await asyncio.to_thread(
                self._statutes_col.query, query_texts=[query], n_results=min(top_k, count)
            )
            return self._parse_query_results(results)
        except Exception as e:
            logger.warning("Search statutes failed: %s", e)
            self._invalidate_connection()
            return []

    # ── Delete ────────────────────────────────────────────────────────────

    async def delete_cases(self, ids: list[str]) -> bool:
        if not await asyncio.to_thread(self._ensure_connection):
            return False
        try:
            await asyncio.to_thread(self._cases_col.delete, ids=ids)
            self._stats_cache = None
            return True
        except Exception as e:
            logger.warning("Delete cases failed: %s", e)
            self._invalidate_connection()
            return False

    async def delete_statutes(self, ids: list[str]) -> bool:
        if not await asyncio.to_thread(self._ensure_connection):
            return False
        try:
            await asyncio.to_thread(self._statutes_col.delete, ids=ids)
            self._stats_cache = None
            return True
        except Exception as e:
            logger.warning("Delete statutes failed: %s", e)
            self._invalidate_connection()
            return False

    async def search_knowledge(self, query: str, top_k: int = 10) -> list[dict]:
        if not query or not query.strip():
            return []
        if not await asyncio.to_thread(self._ensure_connection) or self._knowledge_col is None:
            return []
        try:
            count = self._knowledge_col.count()
            if not count:
                return []
            results = await asyncio.to_thread(
                self._knowledge_col.query, query_texts=[query], n_results=min(top_k, count)
            )
            return self._parse_query_results(results)
        except Exception as e:
            logger.warning("Search knowledge failed: %s", e)
            self._invalidate_connection()
            return []

    async def add_knowledge(self, items: list[dict]) -> int:
        if not await asyncio.to_thread(self._ensure_connection) or not items or self._knowledge_col is None:
            return 0
        ids = [str(it["id"]) for it in items]
        docs = [f"{it.get('title', '')}\n{it['content']}" for it in items]
        metas = [it.get("metadata", {}) for it in items]
        try:
            await asyncio.to_thread(
                self._knowledge_col.upsert, ids=ids, documents=docs, metadatas=metas
            )
            self._stats_cache = None
            return len(ids)
        except Exception as e:
            logger.error("Add knowledge failed: %s", e)
            self._invalidate_connection()
            return 0

    async def delete_knowledge(self, ids: list[str]) -> bool:
        if not await asyncio.to_thread(self._ensure_connection) or self._knowledge_col is None:
            return False
        try:
            await asyncio.to_thread(self._knowledge_col.delete, ids=ids)
            self._stats_cache = None
            return True
        except Exception as e:
            logger.warning("Delete knowledge failed: %s", e)
            self._invalidate_connection()
            return False

    # ── Stats (with caching) ─────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Return collection stats with a 5-second cache to avoid repeated
        ``.count()`` calls on ChromaDB.
        """
        now = time.monotonic()
        if self._stats_cache is not None:
            cache_ts, cached = self._stats_cache
            if now - cache_ts < _STATS_CACHE_TTL:
                return cached

        if not await asyncio.to_thread(self._ensure_connection):
            return {"cases_count": 0, "statutes_count": 0, "connected": False}
        try:
            cases_count = await asyncio.to_thread(self._cases_col.count)
            statutes_count = await asyncio.to_thread(self._statutes_col.count)
            knowledge_count = (
                await asyncio.to_thread(self._knowledge_col.count)
                if self._knowledge_col
                else 0
            )
            stats = {
                "cases_count": cases_count,
                "statutes_count": statutes_count,
                "knowledge_count": knowledge_count,
                "connected": True,
            }
            self._stats_cache = (now, stats)
            return stats
        except Exception:
            self._invalidate_connection()
            return {"cases_count": 0, "statutes_count": 0, "knowledge_count": 0, "connected": False}

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _parse_query_results(results: dict) -> list[dict]:
        """Parse ChromaDB query results into a list of dicts."""
        items: list[dict] = []
        documents = results.get("documents") or [[]]
        ids_list = results.get("ids") or [[]]
        metas_list = results.get("metadatas") or [[]]
        dists_list = results.get("distances") or [[]]

        for i, doc in enumerate(documents[0] if documents else []):
            items.append({
                "id": ids_list[0][i] if i < len(ids_list[0]) else str(i),
                "content": doc,
                "metadata": metas_list[0][i] if i < len(metas_list[0]) else {},
                "distance": dists_list[0][i] if i < len(dists_list[0]) else 0,
            })
        return items
