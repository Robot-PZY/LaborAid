"""SSE / 流式响应的数据库会话包装 — 避免 get_db 在流开始前就 commit/close。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal


def wrap_stream_with_db(
    factory: Callable[[AsyncSession], AsyncIterator[str]],
) -> Callable[[], AsyncIterator[str]]:
    """在流式生成器生命周期内持有独立 session，结束时 commit。"""

    async def _wrapper() -> AsyncIterator[str]:
        async with AsyncSessionLocal() as session:
            try:
                async for chunk in factory(session):
                    yield chunk
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _wrapper
