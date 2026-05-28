"""Performance monitoring utilities for LaborAid.

Provides:
- ``timed`` decorator for measuring async function execution time
- Slow query logging (queries > 1s)
- LLM call timing and cost estimation
- Memory usage monitoring
"""

import functools
import logging
import threading
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("app.monitoring")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SLOW_QUERY_THRESHOLD_MS = 1000  # Log warning if query takes > 1 second


# ---------------------------------------------------------------------------
# Timing data store (in-memory, bounded)
# ---------------------------------------------------------------------------

@dataclass
class TimingRecord:
    """A single timing measurement."""
    name: str
    elapsed_ms: float
    timestamp: float
    metadata: dict = field(default_factory=dict)


class TimingStore:
    """Thread-safe in-memory store for timing records (capped at last N).

    Uses a threading lock to ensure safe concurrent access and LRU eviction
    to drop the oldest record when max_records is reached.
    """

    def __init__(self, max_records: int = 1000):
        self._records: list[TimingRecord] = []
        self._max = max_records
        self._lock = threading.Lock()

    def add(self, record: TimingRecord) -> None:
        with self._lock:
            if len(self._records) >= self._max:
                # LRU eviction: remove the oldest record
                self._records.pop(0)
            self._records.append(record)

    def recent(self, n: int = 50) -> list[TimingRecord]:
        with self._lock:
            return list(self._records[-n:])

    def slow_queries(self, threshold_ms: float = SLOW_QUERY_THRESHOLD_MS) -> list[TimingRecord]:
        with self._lock:
            return [r for r in self._records if r.elapsed_ms >= threshold_ms]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._records)


# Global timing store
timing_store = TimingStore()


# ---------------------------------------------------------------------------
# ``timed`` decorator
# ---------------------------------------------------------------------------

def timed(
    name: str | None = None,
    *,
    slow_threshold_ms: float = SLOW_QUERY_THRESHOLD_MS,
    log_level: int = logging.DEBUG,
    metadata: dict | None = None,
) -> Callable:
    """Decorator that measures and logs the execution time of an async function.

    Usage::

        @timed("my_function")
        async def my_function(arg1):
            ...

        # Or with custom threshold:
        @timed("expensive_op", slow_threshold_ms=5000)
        async def expensive_op():
            ...
    """

    def decorator(func: Callable) -> Callable:
        label = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.monotonic() - start) * 1000
                record = TimingRecord(
                    name=label,
                    elapsed_ms=elapsed_ms,
                    timestamp=time.time(),
                    metadata=metadata or {},
                )
                timing_store.add(record)

                if elapsed_ms >= slow_threshold_ms:
                    logger.warning(
                        "SLOW QUERY: %s took %.1fms (threshold=%dms)",
                        label, elapsed_ms, slow_threshold_ms,
                    )
                else:
                    logger.log(
                        log_level,
                        "TIMED %s: %.1fms",
                        label, elapsed_ms,
                    )

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# LLM call timing and cost estimation
# ---------------------------------------------------------------------------

@dataclass
class LLMCallMetrics:
    """Metrics from a single LLM API call."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_ms: float = 0.0
    estimated_cost_usd: float = 0.0


# Rough cost per 1K tokens (USD) for common models — update as pricing changes.
_COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    # model -> {"input": cost, "output": cost}
    "glm-5.1": {"input": 0.003, "output": 0.015},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}

# Fallback pricing
_DEFAULT_COST = {"input": 0.003, "output": 0.015}


def estimate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of an LLM call in USD.

    Uses a simple lookup table; falls back to default rates for unknown models.
    """
    pricing = _COST_PER_1K_TOKENS.get(model, _DEFAULT_COST)
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def record_llm_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    elapsed_ms: float,
) -> LLMCallMetrics:
    """Record a completed LLM call with timing and cost estimation.

    Returns the metrics for logging or further use.
    """
    cost = estimate_llm_cost(model, input_tokens, output_tokens)
    metrics = LLMCallMetrics(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        elapsed_ms=elapsed_ms,
        estimated_cost_usd=cost,
    )
    timing_store.add(TimingRecord(
        name=f"llm_call:{model}",
        elapsed_ms=elapsed_ms,
        timestamp=time.time(),
        metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost,
        },
    ))
    logger.info(
        "LLM call: model=%s in=%d out=%d cost=$%.6f elapsed=%.0fms",
        model, input_tokens, output_tokens, cost, elapsed_ms,
    )
    return metrics


class LLMTimer:
    """Context manager for timing LLM calls.

    Usage::

        with LLMTimer("glm-5.1") as t:
            response = await client.messages.create(...)

        # Access metrics after the block:
        print(t.elapsed_ms, t.estimated_cost)
    """

    def __init__(self, model: str):
        self.model = model
        self.start: float = 0
        self.elapsed_ms: float = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.estimated_cost: float = 0
        self._metrics: LLMCallMetrics | None = None

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.monotonic() - self.start) * 1000
        if self.input_tokens or self.output_tokens:
            self._metrics = record_llm_call(
                self.model, self.input_tokens, self.output_tokens, self.elapsed_ms
            )
            self.estimated_cost = self._metrics.estimated_cost_usd
        return False

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Set token counts from the LLM response."""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


# ---------------------------------------------------------------------------
# Memory usage monitoring
# ---------------------------------------------------------------------------

def get_memory_usage() -> dict:
    """Return current process memory usage information.

    Uses ``tracemalloc`` if available, otherwise falls back to a basic approach.
    """
    result = {
        "tracemalloc_active": False,
    }

    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        result["tracemalloc_active"] = True
        result["current_mb"] = round(current / 1024 / 1024, 2)
        result["peak_mb"] = round(peak / 1024 / 1024, 2)
    else:
        # Try to start tracemalloc (best-effort)
        try:
            tracemalloc.start()
            current, peak = tracemalloc.get_traced_memory()
            result["tracemalloc_active"] = True
            result["current_mb"] = round(current / 1024 / 1024, 2)
            result["peak_mb"] = round(peak / 1024 / 1024, 2)
        except Exception:
            pass

    # Timing store stats
    result["timing_records"] = timing_store.count
    result["slow_queries"] = len(timing_store.slow_queries())

    return result


def get_performance_summary() -> dict:
    """Return a summary of performance metrics for admin dashboards."""
    recent = timing_store.recent(50)
    slow = timing_store.slow_queries()

    # Compute average elapsed by operation name
    by_name: dict[str, list[float]] = {}
    for r in recent:
        by_name.setdefault(r.name, []).append(r.elapsed_ms)

    avg_by_name = {
        name: round(sum(times) / len(times), 2)
        for name, times in by_name.items()
    }

    return {
        "total_records": timing_store.count,
        "slow_query_count": len(slow),
        "recent_avg_ms_by_operation": avg_by_name,
        "memory": get_memory_usage(),
    }
