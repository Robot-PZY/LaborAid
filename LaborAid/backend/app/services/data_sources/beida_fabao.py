"""北大法宝MCP适配器 — LegalDataSourceAdapter实现

增强功能:
- 子进程超时保护（不会无限挂起）
- 非JSON输出容错处理
- MCP未安装检测与友好中文提示
- 相同查询60秒TTL缓存
- 全中文错误消息
"""

import json
import asyncio
import logging
import shutil
import time
from typing import Any

from app.services.data_sources.base import (
    LegalDataSourceAdapter,
    LawSearchResult,
    CaseSearchResult,
    DataSourceRegistry,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 简易内存缓存（60秒TTL）
# ---------------------------------------------------------------------------
_CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    """Return cached value if still fresh, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.monotonic() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


# ---------------------------------------------------------------------------
# MCP可用性检测（惰性检查，结果缓存5分钟）
# ---------------------------------------------------------------------------
_mcp_available: bool | None = None
_mcp_check_ts: float = 0
_MCP_CHECK_INTERVAL = 300  # seconds


def _is_mcp_available() -> tuple[bool, str]:
    """Check whether the chinese-law-mcp npm package is installed.

    Returns (available, error_message).
    """
    global _mcp_available, _mcp_check_ts

    now = time.monotonic()
    if _mcp_available is not None and (now - _mcp_check_ts) < _MCP_CHECK_INTERVAL:
        if _mcp_available:
            return True, ""
        return False, "北大法宝MCP服务未安装或不可用。请运行: npm install -g @ansvar/chinese-law-mcp"

    # Check if npx is available
    if not shutil.which("npx"):
        _mcp_available = False
        _mcp_check_ts = now
        return False, "系统未安装 npx，无法调用北大法宝MCP服务。请先安装 Node.js。"

    _mcp_available = True
    _mcp_check_ts = now
    return True, ""


# ---------------------------------------------------------------------------
# 子进程调用封装
# ---------------------------------------------------------------------------
_MCP_TIMEOUT = 30  # seconds for search
_MCP_HEALTH_TIMEOUT = 15  # seconds for health check


async def _run_mcp(payload: dict, timeout: int = _MCP_TIMEOUT) -> dict | None:
    """Run the MCP subprocess with proper timeout, JSON-error, and
    not-installed handling.

    Returns parsed JSON dict on success, None on any failure.
    """
    # Check MCP availability first
    available, err_msg = _is_mcp_available()
    if not available:
        logger.warning("MCP not available: %s", err_msg)
        return None

    stdin_text = json.dumps(payload, ensure_ascii=False)

    try:
        result = await asyncio.to_thread(
            _run_subprocess,
            stdin_text,
            timeout,
        )
    except asyncio.TimeoutError:
        logger.error("北大法宝MCP调用超时（%d秒），查询: %s", timeout, payload.get("query", "")[:50])
        # Mark MCP as potentially unavailable after timeout
        global _mcp_available
        _mcp_available = None
        return None
    except Exception as e:
        logger.error("北大法宝MCP调用异常: %s", e)
        return None

    if result is None:
        return None

    return result


def _run_subprocess(stdin_text: str, timeout: int) -> dict | None:
    """Synchronous subprocess runner (called via to_thread)."""
    try:
        proc = __import__("subprocess").run(
            ["npx", "-y", "@ansvar/chinese-law-mcp@latest"],
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_text,
        )
    except __import__("subprocess").TimeoutExpired:
        raise asyncio.TimeoutError()
    except FileNotFoundError:
        # npx not found
        global _mcp_available
        _mcp_available = False
        return None

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        logger.warning(
            "北大法宝MCP返回错误码 %d: %s",
            proc.returncode,
            stderr[:200],
        )
        return None

    stdout = (proc.stdout or "").strip()
    if not stdout:
        logger.warning("北大法宝MCP返回空输出")
        return None

    # Try to parse JSON — handle non-JSON output gracefully
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # The MCP server might output diagnostic lines before the JSON
        # Try to find JSON in the output
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        logger.warning(
            "北大法宝MCP返回非JSON输出: %s",
            stdout[:200],
        )
        return None


class BeidaFabaoAdapter(LegalDataSourceAdapter):
    name = "beida_fabao"
    description = "北大法宝法律法规数据库"
    supported_types = ["law"]

    async def search_law(self, query: str, limit: int = 10, **filters) -> list[LawSearchResult]:
        if not query or not query.strip():
            return []

        # Check cache
        cache_key = f"search_law:{query.strip()}:{limit}"
        cached = _cache_get(cache_key)
        if cached is not None:
            logger.debug("北大法宝缓存命中: %s", query[:30])
            return cached

        payload = {"method": "search", "query": query, "limit": limit}
        data = await _run_mcp(payload)

        if data is None:
            return []

        items = data if isinstance(data, list) else data.get("results", [])
        results = [
            LawSearchResult(
                source="北大法宝",
                document_id=it.get("document_id", ""),
                title=it.get("title", ""),
                provision_ref=it.get("provision_ref", ""),
                content=it.get("snippet", it.get("content", ""))[:500],
                relevance_score=it.get("relevance_score", 0.5),
            ) for it in items[:limit]
        ]

        if results:
            _cache_set(cache_key, results)

        return results

    async def search_case(self, query: str, limit: int = 10, **filters) -> list[CaseSearchResult]:
        # 北大法宝MCP主要支持法规，案例检索后续扩展
        return []

    async def get_provision(self, doc_id: str, article: str = None) -> dict | None:
        if not doc_id:
            return None

        cache_key = f"get_provision:{doc_id}:{article or ''}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        payload = {"method": "get", "document_id": doc_id, "article": article}
        data = await _run_mcp(payload)

        if data is not None:
            _cache_set(cache_key, data)

        return data

    async def health_check(self) -> bool:
        try:
            result = await asyncio.to_thread(
                _run_subprocess,
                "",
                _MCP_HEALTH_TIMEOUT,
            )
            return result is not None
        except Exception as e:
            logger.warning("北大法宝 health_check 失败: %s", e)
            return False


def register_beida_fabao():
    """注册北大法宝适配器到DataSourceRegistry"""
    adapter = BeidaFabaoAdapter()
    DataSourceRegistry.register(adapter)
    logger.info("BeidaFabao adapter registered")
