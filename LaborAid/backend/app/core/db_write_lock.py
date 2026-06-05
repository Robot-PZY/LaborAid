"""SQLite 单写锁 — 避免并发写入导致 database is locked。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

_sqlite_write_lock = asyncio.Lock()


async def run_serialized_write(fn: Callable[[], Awaitable[T]]) -> T:
    async with _sqlite_write_lock:
        return await fn()
