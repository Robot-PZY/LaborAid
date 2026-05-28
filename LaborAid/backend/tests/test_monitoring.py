"""Tests for the monitoring module (app.core.monitoring).

Covers: TimingStore thread safety / LRU eviction, TimingRecord __slots__,
the ``timed`` decorator, LLM cost estimation, record_llm_call, LLMTimer
context manager, get_memory_usage, and get_performance_summary.
"""

import asyncio
import threading
import time

import pytest

from app.core.monitoring import (
    LLMTimer,
    LLMCallMetrics,
    TimingRecord,
    TimingStore,
    estimate_llm_cost,
    get_memory_usage,
    get_performance_summary,
    record_llm_call,
    timed,
    timing_store,
)


# ---------------------------------------------------------------------------
# TimingRecord
# ---------------------------------------------------------------------------


class TestTimingRecord:
    """Tests for the TimingRecord dataclass."""

    def test_is_dataclass(self):
        """TimingRecord should be a dataclass."""
        from dataclasses import fields
        field_names = {f.name for f in fields(TimingRecord)}
        assert field_names == {"name", "elapsed_ms", "timestamp", "metadata"}

    def test_record_creation_with_defaults(self):
        """metadata should default to an empty dict."""
        rec = TimingRecord(name="test", elapsed_ms=42.0, timestamp=1000.0)
        assert rec.name == "test"
        assert rec.elapsed_ms == 42.0
        assert rec.timestamp == 1000.0
        assert rec.metadata == {}

    def test_record_creation_with_metadata(self):
        """Custom metadata should be stored correctly."""
        meta = {"key": "value"}
        rec = TimingRecord(name="op", elapsed_ms=10.0, timestamp=0.0, metadata=meta)
        assert rec.metadata == meta


# ---------------------------------------------------------------------------
# TimingStore — basic operations
# ---------------------------------------------------------------------------


class TestTimingStoreBasic:
    """Tests for TimingStore basic add / recent / count / clear."""

    def test_add_and_count(self):
        store = TimingStore(max_records=10)
        store.add(TimingRecord(name="a", elapsed_ms=1.0, timestamp=0.0))
        store.add(TimingRecord(name="b", elapsed_ms=2.0, timestamp=0.0))
        assert store.count == 2

    def test_recent_returns_latest(self):
        store = TimingStore(max_records=10)
        for i in range(5):
            store.add(TimingRecord(name=f"op_{i}", elapsed_ms=float(i), timestamp=0.0))
        recent = store.recent(n=3)
        assert len(recent) == 3
        assert recent[0].name == "op_2"
        assert recent[2].name == "op_4"

    def test_recent_respects_n_parameter(self):
        store = TimingStore(max_records=100)
        for i in range(50):
            store.add(TimingRecord(name=f"op_{i}", elapsed_ms=0.0, timestamp=0.0))
        assert len(store.recent(10)) == 10
        assert len(store.recent(100)) == 50

    def test_clear_empties_store(self):
        store = TimingStore()
        store.add(TimingRecord(name="a", elapsed_ms=1.0, timestamp=0.0))
        assert store.count == 1
        store.clear()
        assert store.count == 0

    def test_slow_queries_filters_by_threshold(self):
        store = TimingStore()
        store.add(TimingRecord(name="fast", elapsed_ms=50.0, timestamp=0.0))
        store.add(TimingRecord(name="slow", elapsed_ms=1500.0, timestamp=0.0))
        store.add(TimingRecord(name="also_slow", elapsed_ms=2000.0, timestamp=0.0))
        slow = store.slow_queries(threshold_ms=1000)
        assert len(slow) == 2
        assert all(r.elapsed_ms >= 1000 for r in slow)

    def test_slow_queries_default_threshold(self):
        store = TimingStore()
        store.add(TimingRecord(name="at_boundary", elapsed_ms=1000.0, timestamp=0.0))
        store.add(TimingRecord(name="below", elapsed_ms=999.0, timestamp=0.0))
        slow = store.slow_queries()
        assert len(slow) == 1
        assert slow[0].name == "at_boundary"


# ---------------------------------------------------------------------------
# TimingStore — LRU eviction
# ---------------------------------------------------------------------------


class TestTimingStoreLRU:
    """Tests for TimingStore LRU eviction when max_records is reached."""

    def test_eviction_removes_oldest(self):
        store = TimingStore(max_records=3)
        store.add(TimingRecord(name="first", elapsed_ms=1.0, timestamp=0.0))
        store.add(TimingRecord(name="second", elapsed_ms=2.0, timestamp=0.0))
        store.add(TimingRecord(name="third", elapsed_ms=3.0, timestamp=0.0))
        # At capacity — next add should evict "first"
        store.add(TimingRecord(name="fourth", elapsed_ms=4.0, timestamp=0.0))
        assert store.count == 3
        recent = store.recent(100)
        names = [r.name for r in recent]
        assert "first" not in names
        assert "fourth" in names

    def test_eviction_keeps_most_recent(self):
        store = TimingStore(max_records=2)
        store.add(TimingRecord(name="a", elapsed_ms=1.0, timestamp=0.0))
        store.add(TimingRecord(name="b", elapsed_ms=2.0, timestamp=0.0))
        store.add(TimingRecord(name="c", elapsed_ms=3.0, timestamp=0.0))
        store.add(TimingRecord(name="d", elapsed_ms=4.0, timestamp=0.0))
        recent = store.recent(100)
        assert len(recent) == 2
        assert recent[0].name == "c"
        assert recent[1].name == "d"


# ---------------------------------------------------------------------------
# TimingStore — thread safety
# ---------------------------------------------------------------------------


class TestTimingStoreThreadSafety:
    """Tests for concurrent access to TimingStore."""

    def test_concurrent_adds_no_data_loss(self):
        """Many threads adding simultaneously should not lose records."""
        store = TimingStore(max_records=500)
        num_threads = 10
        adds_per_thread = 20
        barrier = threading.Barrier(num_threads)

        def worker():
            barrier.wait()
            for i in range(adds_per_thread):
                store.add(TimingRecord(name=f"t-{i}", elapsed_ms=float(i), timestamp=0.0))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * adds_per_thread
        assert store.count == expected

    def test_concurrent_adds_with_small_max(self):
        """With a small max_records, concurrent adds should not exceed the cap."""
        max_records = 50
        store = TimingStore(max_records=max_records)
        barrier = threading.Barrier(5)

        def worker():
            barrier.wait()
            for i in range(100):
                store.add(TimingRecord(name=f"t-{i}", elapsed_ms=float(i), timestamp=0.0))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert store.count <= max_records


# ---------------------------------------------------------------------------
# ``timed`` decorator
# ---------------------------------------------------------------------------


class TestTimedDecorator:
    """Tests for the ``timed`` async decorator."""

    @pytest.mark.asyncio
    async def test_timed_records_execution(self):
        """Decorated async function should record its timing in the global store."""
        store_before = timing_store.count

        @timed("test_op")
        async def dummy():
            await asyncio.sleep(0.01)
            return "done"

        result = await dummy()
        assert result == "done"
        assert timing_store.count > store_before

        # Find the record we just added
        recent = timing_store.recent(10)
        matches = [r for r in recent if r.name == "test_op"]
        assert len(matches) >= 1
        assert matches[-1].elapsed_ms > 0

    @pytest.mark.asyncio
    async def test_timed_default_name(self):
        """When no name is provided, use module.qualname."""
        @timed()
        async def my_function():
            return 42

        await my_function()
        recent = timing_store.recent(10)
        names = [r.name for r in recent]
        assert any("my_function" in n for n in names)

    @pytest.mark.asyncio
    async def test_timed_preserves_return_value(self):
        """Decorator should not alter the function's return value."""
        @timed("preserve_test")
        async def returns_list():
            return [1, 2, 3]

        result = await returns_list()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_timed_propagates_exception(self):
        """Exceptions from the decorated function should propagate."""
        @timed("failing_op")
        async def raises():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await raises()


# ---------------------------------------------------------------------------
# LLM cost estimation
# ---------------------------------------------------------------------------


class TestEstimateLLMCost:
    """Tests for estimate_llm_cost."""

    def test_known_model(self):
        """A model in the pricing table should return the correct cost."""
        # glm-5.1: input 0.003/1K, output 0.015/1k
        cost = estimate_llm_cost("glm-5.1", input_tokens=1000, output_tokens=1000)
        assert cost == pytest.approx(0.018, abs=1e-6)

    def test_known_model_zero_tokens(self):
        """Zero tokens should produce zero cost."""
        cost = estimate_llm_cost("glm-5.1", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_unknown_model_uses_default(self):
        """An unknown model should fall back to default pricing."""
        cost_default = estimate_llm_cost("glm-5.1", input_tokens=1000, output_tokens=1000)
        cost_unknown = estimate_llm_cost("nonexistent-model-xyz", input_tokens=1000, output_tokens=1000)
        # The default rates happen to match glm-5.1 in the current config,
        # so the costs should be equal.
        assert cost_unknown == cost_default

    def test_cost_only_input(self):
        cost = estimate_llm_cost("glm-5.1", input_tokens=2000, output_tokens=0)
        assert cost == pytest.approx(0.006, abs=1e-6)

    def test_cost_only_output(self):
        cost = estimate_llm_cost("glm-5.1", input_tokens=0, output_tokens=2000)
        assert cost == pytest.approx(0.030, abs=1e-6)


# ---------------------------------------------------------------------------
# record_llm_call
# ---------------------------------------------------------------------------


class TestRecordLLMCall:
    """Tests for record_llm_call."""

    def test_returns_metrics(self):
        metrics = record_llm_call(
            model="glm-5.1",
            input_tokens=500,
            output_tokens=200,
            elapsed_ms=1200.0,
        )
        assert isinstance(metrics, LLMCallMetrics)
        assert metrics.model == "glm-5.1"
        assert metrics.input_tokens == 500
        assert metrics.output_tokens == 200
        assert metrics.elapsed_ms == 1200.0
        assert metrics.estimated_cost_usd > 0

    def test_adds_to_timing_store(self):
        count_before = timing_store.count
        record_llm_call(model="glm-5.1", input_tokens=100, output_tokens=50, elapsed_ms=100.0)
        assert timing_store.count == count_before + 1

        recent = timing_store.recent(1)
        record = recent[0]
        assert record.name == "llm_call:glm-5.1"
        assert record.metadata["input_tokens"] == 100
        assert record.metadata["output_tokens"] == 50

    def test_metrics_cost_matches_estimate(self):
        metrics = record_llm_call(model="glm-5.1", input_tokens=1000, output_tokens=500, elapsed_ms=300.0)
        expected = estimate_llm_cost("glm-5.1", 1000, 500)
        assert metrics.estimated_cost_usd == expected


# ---------------------------------------------------------------------------
# LLMTimer context manager
# ---------------------------------------------------------------------------


class TestLLMTimer:
    """Tests for the LLMTimer context manager."""

    def test_elapsed_ms_set_after_exit(self):
        with LLMTimer("glm-5.1") as t:
            time.sleep(0.01)
        assert t.elapsed_ms > 0

    def test_set_tokens_and_cost(self):
        with LLMTimer("glm-5.1") as t:
            t.set_tokens(input_tokens=1000, output_tokens=500)
        assert t.input_tokens == 1000
        assert t.output_tokens == 500
        assert t.estimated_cost > 0

    def test_no_cost_without_tokens(self):
        with LLMTimer("glm-5.1") as t:
            pass  # no tokens set
        assert t.estimated_cost == 0

    def test_records_to_timing_store_when_tokens_set(self):
        count_before = timing_store.count
        with LLMTimer("glm-5.1") as t:
            t.set_tokens(100, 50)
        assert timing_store.count == count_before + 1


# ---------------------------------------------------------------------------
# get_memory_usage
# ---------------------------------------------------------------------------


class TestGetMemoryUsage:
    """Tests for get_memory_usage."""

    def test_returns_dict(self):
        result = get_memory_usage()
        assert isinstance(result, dict)

    def test_contains_expected_keys(self):
        result = get_memory_usage()
        assert "tracemalloc_active" in result
        assert "timing_records" in result
        assert "slow_queries" in result

    def test_timing_records_is_int(self):
        result = get_memory_usage()
        assert isinstance(result["timing_records"], int)

    def test_tracemalloc_active_is_bool(self):
        result = get_memory_usage()
        assert isinstance(result["tracemalloc_active"], bool)


# ---------------------------------------------------------------------------
# get_performance_summary
# ---------------------------------------------------------------------------


class TestGetPerformanceSummary:
    """Tests for get_performance_summary."""

    def test_returns_dict(self):
        summary = get_performance_summary()
        assert isinstance(summary, dict)

    def test_contains_expected_keys(self):
        summary = get_performance_summary()
        assert "total_records" in summary
        assert "slow_query_count" in summary
        assert "recent_avg_ms_by_operation" in summary
        assert "memory" in summary

    def test_total_records_is_int(self):
        summary = get_performance_summary()
        assert isinstance(summary["total_records"], int)

    def test_memory_is_dict(self):
        summary = get_performance_summary()
        assert isinstance(summary["memory"], dict)

    def test_recent_avg_ms_by_operation_is_dict(self):
        summary = get_performance_summary()
        assert isinstance(summary["recent_avg_ms_by_operation"], dict)
