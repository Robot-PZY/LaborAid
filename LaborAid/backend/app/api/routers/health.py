"""Health check endpoint — detailed component-level status."""

import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.security import get_current_user, require_admin
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

_VERSION = "0.1.0"


async def _check_database() -> dict:
    """Check database connectivity."""
    try:
        from app.core.database import db_health_check
        result = await db_health_check()
        return {"status": result.get("status", "ok"), "latency_ms": result.get("latency_ms")}
    except Exception:
        return {"status": "error"}


async def _check_chromadb() -> dict:
    """Check ChromaDB vector store connectivity."""
    try:
        from app.services.vector.store import get_vector_service
        svc = get_vector_service()
        start = time.monotonic()
        connected = svc._ensure_connection()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        if connected:
            return {"status": "ok", "latency_ms": latency_ms}
        return {"status": "unavailable", "latency_ms": latency_ms}
    except Exception:
        return {"status": "error"}


async def _check_llm() -> dict:
    """Check LLM API connectivity (best-effort, non-blocking)."""
    try:
        from app.config import get_settings
        settings = get_settings()
        if not settings.LLM_API_KEY:
            return {"status": "not_configured"}
        from app.services.llm_client import create_llm_client_from_settings
        create_llm_client_from_settings(settings)
        return {"status": "configured", "model": settings.LLM_MODEL}
    except Exception:
        return {"status": "error"}


@router.get("/health")
async def health_check():
    """Return detailed health status with component-level checks."""
    start = time.monotonic()

    db_status = await _check_database()
    chroma_status = await _check_chromadb()
    llm_status = await _check_llm()

    total_latency = round((time.monotonic() - start) * 1000, 2)

    # Overall status: "ok" only if database (critical) is healthy.
    # ChromaDB and LLM are non-critical — degraded status if they're down.
    overall = "ok" if db_status.get("status") == "ok" else "degraded"
    if db_status.get("status") == "error":
        overall = "error"

    return JSONResponse(
        status_code=200 if overall != "error" else 503,
        content={
            "status": overall,
            "app": "LaborAid",
            "version": _VERSION,
            "latency_ms": total_latency,
            "components": {
                "database": db_status,
                "chromadb": chroma_status,
                "llm": llm_status,
            },
        },
    )


@router.get("/performance")
async def performance_stats(current_user: User = Depends(get_current_user)):
    """Return performance monitoring statistics. Admin only."""
    require_admin(current_user)
    from app.core.monitoring import get_performance_summary
    return get_performance_summary()
