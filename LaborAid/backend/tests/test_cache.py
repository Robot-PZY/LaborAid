"""Tests for app.core.cache – TTL-based in-memory cache, key helpers,
get_or_set, increment, stats, delete_pattern, and eviction.
"""

import time

import pytest

from app.core.cache import Cache, cache_key


# ---------------------------------------------------------------------------
# 1. Cache set / get round-trip
# ---------------------------------------------------------------------------

class TestCacheSetGet:
    """Basic set and get operations."""

    def test_set_and_get(self):
        c = Cache(default_ttl=60)
        c.set("k1", "value1")
        assert c.get("k1") == "value1"

    def test_get_missing_key_returns_none(self):
        c = Cache()
        assert c.get("nonexistent") is None

    def test_set_overwrite(self):
        c = Cache()
        c.set("k", "first")
        c.set("k", "second")
        assert c.get("k") == "second"

    def test_various_value_types(self):
        c = Cache()
        c.set("int", 42)
        c.set("list", [1, 2, 3])
        c.set("dict", {"a": 1})
        c.set("none", None)
        assert c.get("int") == 42
        assert c.get("list") == [1, 2, 3]
        assert c.get("dict") == {"a": 1}
        assert c.get("none") is None


# ---------------------------------------------------------------------------
# 2. TTL expiration
# ---------------------------------------------------------------------------

class TestCacheTTL:
    """Values should expire after the configured TTL."""

    def test_value_available_before_ttl(self):
        c = Cache(default_ttl=5)
        c.set("temp", "here")
        assert c.get("temp") == "here"

    def test_value_expires_after_ttl(self):
        c = Cache(default_ttl=0.05)  # 50ms
        c.set("temp", "gone")
        time.sleep(0.1)
        assert c.get("temp") is None

    def test_custom_ttl_per_key(self):
        c = Cache(default_ttl=60)
        c.set("long", "lives", ttl=60)
        c.set("short", "dies", ttl=0.05)
        time.sleep(0.1)
        assert c.get("long") == "lives"
        assert c.get("short") is None

    def test_expired_entry_removed_from_store(self):
        c = Cache(default_ttl=0.05)
        c.set("ephemeral", "data")
        time.sleep(0.1)
        # Accessing triggers lazy removal
        c.get("ephemeral")
        assert "ephemeral" not in c._store


# ---------------------------------------------------------------------------
# 3. Max-size eviction
# ---------------------------------------------------------------------------

class TestCacheEviction:
    """Oldest entries should be evicted when the cache exceeds max_size."""

    def test_evicts_expired_when_over_limit(self):
        c = Cache(default_ttl=60, max_size=3)
        c.set("a", 1, ttl=0.01)
        c.set("b", 2)
        c.set("c", 3)
        time.sleep(0.02)
        # Adding a 4th key triggers eviction, which removes the expired "a"
        c.set("d", 4)
        assert c.get("a") is None
        assert c.get("b") == 2
        assert c.get("d") == 4

    def test_lru_fallback_eviction(self):
        """If no entries are expired, the oldest (smallest timestamp) is evicted."""
        c = Cache(default_ttl=60, max_size=2)
        c.set("first", 1)
        c.set("second", 2)
        # Both entries are still within TTL; adding a third should evict oldest
        c.set("third", 3)
        # "first" should have been evicted
        assert c.get("first") is None
        assert c.get("second") == 2
        assert c.get("third") == 3


# ---------------------------------------------------------------------------
# 4. delete_pattern
# ---------------------------------------------------------------------------

class TestDeletePattern:
    """Delete keys by prefix."""

    def test_delete_matching_prefix(self):
        c = Cache()
        c.set("user:1", "alice")
        c.set("user:2", "bob")
        c.set("doc:1", "contract")
        deleted = c.delete_pattern("user:")
        assert deleted == 2
        assert c.get("user:1") is None
        assert c.get("user:2") is None
        assert c.get("doc:1") == "contract"

    def test_delete_pattern_no_match(self):
        c = Cache()
        c.set("a", 1)
        assert c.delete_pattern("zzz") == 0
        assert c.get("a") == 1

    def test_delete_pattern_empty_cache(self):
        c = Cache()
        assert c.delete_pattern("anything") == 0


# ---------------------------------------------------------------------------
# 5. Stats tracking
# ---------------------------------------------------------------------------

class TestCacheStats:
    """Hit and miss counters, hit rate calculation."""

    def test_initial_stats(self):
        c = Cache(max_size=100)
        s = c.stats()
        assert s["size"] == 0
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_rate"] == 0.0
        assert s["max_size"] == 100

    def test_hit_and_miss_counts(self):
        c = Cache()
        c.set("x", 1)
        c.get("x")   # hit
        c.get("y")   # miss
        s = c.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1

    def test_hit_rate_calculation(self):
        c = Cache()
        c.set("k", "v")
        c.get("k")   # hit
        c.get("k")   # hit
        c.get("no")  # miss
        s = c.stats()
        assert s["hit_rate"] == pytest.approx(0.6667, abs=0.01)

    def test_stats_size_tracks_entries(self):
        c = Cache()
        c.set("a", 1)
        c.set("b", 2)
        assert c.stats()["size"] == 2
        c.delete("a")
        assert c.stats()["size"] == 1


# ---------------------------------------------------------------------------
# 6. cache_key helper
# ---------------------------------------------------------------------------

class TestCacheKey:
    """Deterministic key generation from parts."""

    def test_simple_key(self):
        assert cache_key("users", "list") == "users:list"

    def test_single_part(self):
        assert cache_key("singleton") == "singleton"

    def test_long_key_hashed(self):
        # Keys longer than 100 chars should be SHA256-hashed (truncated to 32)
        long_key = cache_key("a" * 101)
        assert len(long_key) == 32
        # Should be a hex digest
        assert all(c in "0123456789abcdef" for c in long_key)

    def test_deterministic(self):
        assert cache_key("x", "y", "z") == cache_key("x", "y", "z")

    def test_numeric_parts_converted(self):
        key = cache_key("user", 42, "profile")
        assert key == "user:42:profile"


# ---------------------------------------------------------------------------
# 7. get_or_set
# ---------------------------------------------------------------------------

class TestGetOrSet:
    """Compute-if-absent pattern."""

    def test_returns_existing(self):
        c = Cache()
        c.set("key", "original")
        result = c.get_or_set("key", "fallback")
        assert result == "original"

    def test_sets_and_returns_default_when_missing(self):
        c = Cache()
        result = c.get_or_set("new_key", "computed")
        assert result == "computed"
        assert c.get("new_key") == "computed"

    def test_sets_default_when_expired(self):
        c = Cache(default_ttl=0.05)
        c.set("expiring", "old")
        time.sleep(0.1)
        result = c.get_or_set("expiring", "refreshed")
        assert result == "refreshed"

    def test_updates_miss_counter(self):
        c = Cache()
        c.get_or_set("absent", "val")
        assert c.stats()["misses"] == 1

    def test_updates_hit_counter_on_existing(self):
        c = Cache()
        c.set("present", "val")
        c.get_or_set("present", "other")
        assert c.stats()["hits"] == 1


# ---------------------------------------------------------------------------
# 8. increment
# ---------------------------------------------------------------------------

class TestIncrement:
    """Atomic counter increment."""

    def test_first_call_initialises_to_delta(self):
        c = Cache()
        result = c.increment("counter")
        assert result == 1

    def test_increments_existing(self):
        c = Cache()
        c.increment("c")
        c.increment("c")
        c.increment("c")
        assert c.increment("c") == 4

    def test_custom_delta(self):
        c = Cache()
        assert c.increment("by5", delta=5) == 5
        assert c.increment("by5", delta=5) == 10

    def test_negative_delta(self):
        c = Cache()
        c.increment("dec", delta=10)
        assert c.increment("dec", delta=-3) == 7

    def test_non_int_value_replaced(self):
        c = Cache()
        c.set("mixed", "string_value")
        # Should treat the stored non-int value as 0 and add delta
        result = c.increment("mixed", delta=1)
        assert result == 1

    def test_resets_ttl(self):
        c = Cache(default_ttl=0.05)
        c.increment("ttl_test")
        time.sleep(0.03)
        c.increment("ttl_test")  # resets TTL
        time.sleep(0.03)
        # 0.06s total, but the second increment reset the clock at 0.03s
        assert c.get("ttl_test") == 2

    def test_custom_ttl(self):
        c = Cache(default_ttl=60)
        c.increment("ct", ttl=0.05)
        time.sleep(0.1)
        assert c.get("ct") is None
