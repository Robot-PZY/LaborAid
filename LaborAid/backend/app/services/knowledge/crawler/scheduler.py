"""知识库爬虫定时任务 — 每周自动同步官方法规。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.knowledge.crawler.service import LawCrawlService

logger = logging.getLogger(__name__)

_STATE_PATH = Path(__file__).resolve().parents[4] / "data" / "knowledge_crawl_state.json"
_scheduler_task: asyncio.Task | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_state() -> dict[str, Any]:
    if not _STATE_PATH.exists():
        return {}
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_schedule_enabled() -> bool:
    state = _load_state()
    if "enabled" in state:
        return bool(state["enabled"])
    return get_settings().KNOWLEDGE_CRAWL_SCHEDULE_ENABLED


def set_schedule_enabled(enabled: bool) -> dict[str, Any]:
    state = _load_state()
    state["enabled"] = enabled
    state["next_run_at"] = compute_next_run().isoformat()
    _save_state(state)
    return get_schedule_status()


def compute_next_run(from_dt: datetime | None = None) -> datetime:
    settings = get_settings()
    now = from_dt or _utc_now()
    local = now.astimezone()
    target_weekday = settings.KNOWLEDGE_CRAWL_WEEKDAY  # 0=Mon … 6=Sun
    days_ahead = (target_weekday - local.weekday()) % 7
    candidate = local.replace(
        hour=settings.KNOWLEDGE_CRAWL_HOUR,
        minute=settings.KNOWLEDGE_CRAWL_MINUTE,
        second=0,
        microsecond=0,
    ) + timedelta(days=days_ahead)
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate.astimezone(timezone.utc)


def get_schedule_status() -> dict[str, Any]:
    settings = get_settings()
    state = _load_state()
    next_run = state.get("next_run_at")
    if not next_run:
        next_run = compute_next_run().isoformat()
    return {
        "enabled": is_schedule_enabled(),
        "weekday": settings.KNOWLEDGE_CRAWL_WEEKDAY,
        "hour": settings.KNOWLEDGE_CRAWL_HOUR,
        "minute": settings.KNOWLEDGE_CRAWL_MINUTE,
        "last_run_at": state.get("last_run_at"),
        "last_run_status": state.get("last_run_status"),
        "last_run_summary": state.get("last_run_summary"),
        "next_run_at": next_run,
        "running": state.get("running", False),
    }


async def run_scheduled_crawl(*, trigger: str = "schedule") -> dict[str, Any]:
    """执行一次完整定时同步（核心种子 + 专题发现）。"""
    state = _load_state()
    if state.get("running"):
        logger.info("Knowledge crawl already running, skip (%s)", trigger)
        return get_schedule_status()

    state["running"] = True
    _save_state(state)

    summary: dict[str, Any] = {"trigger": trigger, "success": 0, "failed": 0, "total": 0}
    status = "success"

    try:
        async with AsyncSessionLocal() as db:
            admin = (
                await db.execute(select(User).where(User.role == "admin").limit(1))
            ).scalar_one_or_none()
            if not admin:
                raise RuntimeError("未找到管理员账号，无法执行定时同步")

            svc = LawCrawlService()
            result = await svc.run(
                db,
                admin,
                include_statutes=True,
                include_topic_discovery=True,
            )
            summary.update({
                "success": result.success,
                "failed": result.failed,
                "total": result.total,
            })
            if result.failed:
                status = "partial" if result.success else "failed"
    except Exception as e:
        logger.exception("Scheduled knowledge crawl failed: %s", e)
        status = "failed"
        summary["error"] = str(e)
    finally:
        state = _load_state()
        state["running"] = False
        state["last_run_at"] = _utc_now().isoformat()
        state["last_run_status"] = status
        state["last_run_summary"] = summary
        state["next_run_at"] = compute_next_run().isoformat()
        _save_state(state)

    logger.info("Scheduled knowledge crawl finished: %s", summary)
    return get_schedule_status()


async def _scheduler_loop() -> None:
    logger.info("Knowledge crawl scheduler started")
    while True:
        try:
            if not is_schedule_enabled():
                await asyncio.sleep(3600)
                continue

            state = _load_state()
            next_raw = state.get("next_run_at")
            next_run = datetime.fromisoformat(next_raw) if next_raw else compute_next_run()
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            delay = (next_run - _utc_now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(min(delay, 3600))
                continue

            await run_scheduled_crawl(trigger="schedule")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Knowledge crawl scheduler cancelled")
            raise
        except Exception as e:
            logger.warning("Scheduler loop error: %s", e)
            await asyncio.sleep(300)


def start_scheduler() -> asyncio.Task | None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return _scheduler_task
    state = _load_state()
    if "next_run_at" not in state:
        state["next_run_at"] = compute_next_run().isoformat()
        if "enabled" not in state:
            state["enabled"] = get_settings().KNOWLEDGE_CRAWL_SCHEDULE_ENABLED
        _save_state(state)
    _scheduler_task = asyncio.create_task(_scheduler_loop(), name="knowledge-crawl-scheduler")
    return _scheduler_task


async def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None
