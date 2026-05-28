"""统一搜索服务 — AI驱动的法律检索"""

import hashlib
import json
import re
import logging
import time
from app.config import get_settings
from app.prompts.persona import prompt_with_persona, SYSTEM_SEARCH
from app.services.llm_client import create_llm_client, create_llm_client_from_settings
from app.schemas.search import (
    UnifiedSearchResult, LawSearchResult, CaseSearchResult,
)
from app.core.monitoring import timed

logger = logging.getLogger(__name__)

_settings = None
_client = None

# ---------------------------------------------------------------------------
# Simple in-memory cache (60s TTL)
# ---------------------------------------------------------------------------
_search_cache: dict[str, tuple[float, UnifiedSearchResult]] = {}
_CACHE_TTL = 60  # seconds


def _cache_key(query: str, result_type: str, top_k: int) -> str:
    raw = f"{query}::{result_type}::{top_k}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str):
    entry = _search_cache.get(key)
    if entry is None:
        return None
    ts, result = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _search_cache[key]
        return None
    return result


def _cache_put(key: str, result: UnifiedSearchResult) -> None:
    _search_cache[key] = (time.monotonic(), result)
    # Evict expired entries periodically (keep cache bounded).
    if len(_search_cache) > 200:
        now = time.monotonic()
        expired = [k for k, (ts, _) in _search_cache.items() if now - ts > _CACHE_TTL]
        for k in expired:
            del _search_cache[k]


# ---------------------------------------------------------------------------
# LLM client singleton
# ---------------------------------------------------------------------------

def _get_client():
    global _client, _settings
    if _client is None:
        _settings = get_settings()
        _client = create_llm_client_from_settings(_settings)
    return _client


LAW_SEARCH_PROMPT = prompt_with_persona("""请根据用户的查询，检索相关的中国法律法规。

查询：{query}

请返回最多{limit}条最相关的法规条文。严格使用以下JSON格式返回，不要返回其他内容：

```json
[
  {{
    "title": "法律法规名称",
    "provision_ref": "第X条",
    "content": "条文核心内容（200字以内）",
    "relevance": 0.95
  }}
]
```

要求：
1. 引用的法规必须真实存在且现行有效
2. 优先引用法律和行政法规，其次引用司法解释
3. relevance分数0-1，越高越相关
4. 如果查询涉及具体案由，引用对应的法律依据""")

CASE_SEARCH_PROMPT = prompt_with_persona("""请根据用户的查询，提供相关典型案例。

查询：{query}

请返回最多{limit}个最相关的典型案例。严格使用以下JSON格式返回：

```json
[
  {{
    "case_number": "案号（如 (2023)京01民初xxx号）",
    "title": "案例标题",
    "court": "审理法院",
    "date": "裁判日期",
    "judgment_type": "判决/裁定/调解",
    "content": "裁判要旨（200字以内）",
    "relevance": 0.90
  }}
]
```

要求：
1. 案例应具有代表性和参考价值
2. 案号格式要规范
3. 裁判要旨要突出核心法律观点""")


def _normalize_relevance(score: float, source: str) -> float:
    """Normalize relevance scores from different sources to 0..1 range."""
    if score is None:
        return 0.5
    # Clamp to [0, 1].
    return max(0.0, min(1.0, float(score)))


def _dedupe_laws(items: list[LawSearchResult]) -> list[LawSearchResult]:
    """Deduplicate law results by title."""
    seen: set[str] = set()
    result = []
    for item in items:
        key = item.title.strip().lower() if item.title else ""
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        result.append(item)
    return result


def _dedupe_cases(items: list[CaseSearchResult]) -> list[CaseSearchResult]:
    """Deduplicate case results by title."""
    seen: set[str] = set()
    result = []
    for item in items:
        key = item.title.strip().lower() if item.title else ""
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        result.append(item)
    return result


class UnifiedSearchService:

    def __init__(self, llm=None):
        self._llm = llm

    def _llm_params(self):
        if self._llm:
            return self._llm.client, self._llm.model, self._llm.max_tokens
        client = _get_client()
        return client, _settings.CLAUDE_MODEL, _settings.CLAUDE_MAX_TOKENS

    @timed("search:unified", slow_threshold_ms=2000)
    async def search(
        self,
        query: str,
        result_type: str = "all",
        sources: list[str] | None = None,
        top_k: int = 20,
    ) -> UnifiedSearchResult:
        # Handle empty query — return empty results instead of erroring.
        if not query or not query.strip():
            return UnifiedSearchResult(
                query=query or "",
                laws=[],
                cases=[],
                total=0,
                sources_used=[],
            )

        # Check cache.
        ckey = _cache_key(query, result_type, top_k)
        cached = _cache_get(ckey)
        if cached is not None:
            return cached

        laws: list[LawSearchResult] = []
        cases: list[CaseSearchResult] = []

        import asyncio

        rt = result_type.lower().rstrip("s")

        tasks = []
        if rt in ("all", "law"):
            tasks.append(self._search_laws_ai(query, min(top_k, 10)))
        else:
            tasks.append(self._empty())

        if rt in ("all", "case"):
            tasks.append(self._search_cases_ai(query, min(top_k, 10)))
        else:
            tasks.append(self._empty())

        # 向量库搜索
        if rt in ("all", "law"):
            tasks.append(self._search_statutes_vector(query, min(top_k, 5)))
        else:
            tasks.append(self._empty())

        if rt in ("all", "case"):
            tasks.append(self._search_cases_vector(query, min(top_k, 5)))
        else:
            tasks.append(self._empty())

        # 外部API搜索
        if rt in ("all", "law"):
            tasks.append(self._search_external_laws(query, min(top_k, 5)))
        else:
            tasks.append(self._empty())

        if rt in ("all", "case"):
            tasks.append(self._search_external_cases(query, min(top_k, 5)))
        else:
            tasks.append(self._empty())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        ai_laws = results[0] if results and not isinstance(results[0], Exception) else []
        ai_cases = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
        vec_statutes = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else []
        vec_cases = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else []
        ext_laws = results[4] if len(results) > 4 and not isinstance(results[4], Exception) else []
        ext_cases = results[5] if len(results) > 5 and not isinstance(results[5], Exception) else []

        # Merge and deduplicate.
        laws = _dedupe_laws(list(ai_laws) + list(vec_statutes) + list(ext_laws))
        cases = _dedupe_cases(list(ai_cases) + list(vec_cases) + list(ext_cases))

        sources_used = []
        if ai_laws:
            sources_used.append("AI法规检索")
        if ai_cases:
            sources_used.append("AI案例检索")
        if vec_statutes:
            sources_used.append("本地法条库")
        if vec_cases:
            sources_used.append("本地案例库")
        if ext_laws:
            sources_used.append("外部法律数据库")
        if ext_cases:
            sources_used.append("外部案例数据库")

        result = UnifiedSearchResult(
            query=query,
            laws=laws,
            cases=cases,
            total=len(laws) + len(cases),
            sources_used=sources_used,
        )

        # Store in cache.
        _cache_put(ckey, result)
        return result

    async def _empty(self):
        return []

    async def _search_laws_ai(self, query: str, limit: int) -> list[LawSearchResult]:
        try:
            client, model, max_tokens = self._llm_params()
            response = await client.messages.create(
                model=model,
                max_tokens=min(max_tokens, 4096),
                system="你是中国法律检索系统。只返回JSON数据，不要其他文字。",
                messages=[{
                    "role": "user",
                    "content": LAW_SEARCH_PROMPT.format(query=query, limit=limit),
                }],
            )
            text = response.content[0].text.strip()
            items = self._parse_json_array(text)
            results = []
            for item in items[:limit]:
                results.append(LawSearchResult(
                    source="AI法规检索",
                    document_id=item.get("title", ""),
                    title=item.get("title", ""),
                    provision_ref=item.get("provision_ref", ""),
                    content=item.get("content", ""),
                    relevance_score=_normalize_relevance(item.get("relevance", 0.5), "ai"),
                ))
            return results
        except Exception as e:
            logger.warning("AI law search failed: %s", e)
            return []

    async def _search_cases_ai(self, query: str, limit: int) -> list[CaseSearchResult]:
        try:
            client, model, max_tokens = self._llm_params()
            response = await client.messages.create(
                model=model,
                max_tokens=min(max_tokens, 4096),
                system="你是中国法律案例检索系统。只返回JSON数据，不要其他文字。",
                messages=[{
                    "role": "user",
                    "content": CASE_SEARCH_PROMPT.format(query=query, limit=limit),
                }],
            )
            text = response.content[0].text.strip()
            items = self._parse_json_array(text)
            results = []
            for item in items[:limit]:
                results.append(CaseSearchResult(
                    source="AI案例检索",
                    case_id=item.get("case_number", ""),
                    case_number=item.get("case_number", ""),
                    title=item.get("title", ""),
                    court=item.get("court", ""),
                    date=item.get("date", ""),
                    judgment_type=item.get("judgment_type", ""),
                    content=item.get("content", ""),
                    relevance_score=_normalize_relevance(item.get("relevance", 0.5), "ai"),
                ))
            return results
        except Exception as e:
            logger.warning("AI case search failed: %s", e)
            return []

    def _parse_json_array(self, text: str) -> list[dict]:
        """Parse a JSON array from LLM response, handling various formats.

        Returns an empty list (never raises) for unparseable text.
        """
        if not text or not text.strip():
            return []
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            # Sometimes LLM wraps in an object with a key.
            if isinstance(result, dict):
                for key in ("results", "data", "items", "laws", "cases"):
                    if key in result and isinstance(result[key], list):
                        return result[key]
            return []
        except json.JSONDecodeError:
            pass
        # Last resort: try to extract a JSON array via regex.
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return []

    async def _search_statutes_vector(self, query: str, limit: int) -> list[LawSearchResult]:
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()
            items = await svc.search_statutes(query, limit)
            results = []
            for it in items:
                meta = it.get("metadata", {})
                results.append(LawSearchResult(
                    source="本地法条库",
                    document_id=it.get("id", ""),
                    title=meta.get("title", ""),
                    provision_ref=meta.get("provision_ref", ""),
                    content=it.get("content", "")[:500],
                    relevance_score=_normalize_relevance(1.0 - it.get("distance", 0.5), "vector"),
                ))
            return results
        except Exception as e:
            logger.warning("Vector statute search failed: %s", e)
            return []

    async def _search_cases_vector(self, query: str, limit: int) -> list[CaseSearchResult]:
        try:
            from app.services.vector.store import get_vector_service
            svc = get_vector_service()
            items = await svc.search_cases(query, limit)
            results = []
            for it in items:
                meta = it.get("metadata", {})
                results.append(CaseSearchResult(
                    source="本地案例库",
                    case_id=it.get("id", ""),
                    case_number=meta.get("case_number", ""),
                    title=meta.get("title", ""),
                    court=meta.get("court", ""),
                    date=meta.get("date", ""),
                    judgment_type=meta.get("judgment_type", ""),
                    content=it.get("content", "")[:500],
                    relevance_score=_normalize_relevance(1.0 - it.get("distance", 0.5), "vector"),
                ))
            return results
        except Exception as e:
            logger.warning("Vector case search failed: %s", e)
            return []

    async def _search_external_laws(self, query: str, limit: int) -> list[LawSearchResult]:
        try:
            from app.services.data_sources.base import DataSourceRegistry
            adapters = DataSourceRegistry.get_all()
            results: list[LawSearchResult] = []
            for name, adapter in adapters.items():
                try:
                    items = await adapter.search_law(query, limit=limit)
                    for item in items:
                        # 兼容 data_sources.base.LawSearchResult 与 dict 两种返回类型
                        payload = item.model_dump() if hasattr(item, "model_dump") else item
                        if isinstance(payload, dict):
                            results.append(LawSearchResult(**payload))
                except Exception as e:
                    logger.warning("外部数据源 %s search_law 失败: %s", name, e)
            return results[:limit]
        except Exception as e:
            logger.warning("外部法律检索失败: %s", e)
            return []

    async def _search_external_cases(self, query: str, limit: int) -> list[CaseSearchResult]:
        try:
            from app.services.data_sources.base import DataSourceRegistry

            adapters = DataSourceRegistry.get_all()
            results: list[CaseSearchResult] = []
            for name, adapter in adapters.items():
                try:
                    items = await adapter.search_case(query, limit=limit)
                    for item in items:
                        # 兼容 data_sources.base.CaseSearchResult 与 dict 两种返回类型
                        payload = item.model_dump() if hasattr(item, "model_dump") else item
                        if isinstance(payload, dict):
                            results.append(CaseSearchResult(**payload))
                except Exception as e:
                    logger.warning("外部数据源 %s search_case 失败: %s", name, e)
            return results[:limit]
        except Exception as e:
            logger.warning("外部案例检索失败: %s", e)
            return []
