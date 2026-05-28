"""Simple TTL-based in-memory cache for LaborAid.

Provides:
- ``Cache`` class with get/set/delete/invalidate operations
- Pre-configured cache instances for common use cases
- Cache invalidation helpers for CRUD operations
"""

import hashlib
import logging
import threading
import time
from typing import Any

logger = logging.getLogger("app.cache")


class Cache:
    """Thread-safe in-memory cache with TTL (time-to-live) support.

    Usage::

        cache = Cache(default_ttl=60)

        # Store a value
        cache.set("key", value, ttl=120)

        # Retrieve
        value = cache.get("key")

        # Delete
        cache.delete("key")

        # Clear all
        cache.clear()

        # Stats
        stats = cache.stats()
    """

    def __init__(self, default_ttl: float = 60.0, max_size: int = 500):
        self._store: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get a cached value by key. Returns None if not found or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value with optional TTL (uses default_ttl if not specified)."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl

        with self._lock:
            self._store[key] = (expires_at, value)
            # Evict expired entries if we hit the size limit
            if len(self._store) > self._max_size:
                self._evict_expired()

    def delete(self, key: str) -> bool:
        """Delete a cached key. Returns True if the key existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def increment(self, key: str, delta: int = 1, ttl: float | None = None) -> int:
        """Atomically increment a cached counter.

        If the key does not exist or is expired, it is initialised to
        ``delta`` (i.e. the first call returns *delta*).  The TTL is reset
        on every call.

        Returns the new value after incrementing.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl

        with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                _, current = entry
                # Guard against non-int stored values
                new_val = (current if isinstance(current, int) else 0) + delta
            else:
                new_val = delta
            self._store[key] = (expires_at, new_val)
            return new_val

    def get_or_set(self, key: str, default: Any, ttl: float | None = None) -> Any:
        """Return the cached value for *key*, or store and return *default*.

        This implements the compute-if-absent pattern: if the key is missing
        (or expired), *default* is stored under *key* and then returned.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                expires_at, value = entry
                if time.monotonic() <= expires_at:
                    self._hits += 1
                    return value
                # Expired — will be replaced below
            self._misses += 1
            new_expires = time.monotonic() + effective_ttl
            self._store[key] = (new_expires, default)
            # Evict if over limit
            if len(self._store) > self._max_size:
                self._evict_expired()
            return default

    def delete_pattern(self, prefix: str) -> int:
        """Delete all keys starting with the given prefix.

        Returns the number of keys deleted.
        """
        with self._lock:
            to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in to_delete:
                del self._store[k]
            return len(to_delete)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }

    def _evict_expired(self) -> None:
        """Remove all expired entries (called under lock).

        If no expired entries are found and we are still over max_size,
        evict the oldest entry (smallest monotonic expiry timestamp).
        """
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        # LRU fallback: if still over limit, remove the oldest entry
        if len(self._store) > self._max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]

    def cleanup(self) -> int:
        """Force cleanup of expired entries. Returns count of removed entries."""
        with self._lock:
            before = len(self._store)
            self._evict_expired()
            return before - len(self._store)


# ---------------------------------------------------------------------------
# Cache key helpers
# ---------------------------------------------------------------------------

def cache_key(*parts: str) -> str:
    """Generate a deterministic cache key from multiple parts.

    Uses SHA256 for long keys to keep them bounded.
    """
    raw = ":".join(str(p) for p in parts)
    if len(raw) > 100:
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    return raw


# ---------------------------------------------------------------------------
# Pre-configured cache instances
# ---------------------------------------------------------------------------

# Vector stats cache (60s TTL)
vector_stats_cache = Cache(default_ttl=60, max_size=50)

# External API presets cache (300s TTL)
presets_cache = Cache(default_ttl=300, max_size=50)

# Knowledge stats cache (60s TTL)
knowledge_stats_cache = Cache(default_ttl=60, max_size=50)

# Search results cache (120s TTL)
search_cache = Cache(default_ttl=120, max_size=200)


# ---------------------------------------------------------------------------
# Cache invalidation helpers
# ---------------------------------------------------------------------------

def invalidate_on_create(resource_type: str, resource_id: int | None = None) -> None:
    """Invalidate relevant caches when a new resource is created."""
    _invalidate_resource(resource_type)


def invalidate_on_update(resource_type: str, resource_id: int | None = None) -> None:
    """Invalidate relevant caches when a resource is updated."""
    _invalidate_resource(resource_type)
    # Also invalidate specific item caches
    if resource_id is not None:
        key = cache_key(resource_type, "item", resource_id)
        search_cache.delete(key)


def invalidate_on_delete(resource_type: str, resource_id: int | None = None) -> None:
    """Invalidate relevant caches when a resource is deleted."""
    _invalidate_resource(resource_type)
    if resource_id is not None:
        key = cache_key(resource_type, "item", resource_id)
        search_cache.delete(key)


def _invalidate_resource(resource_type: str) -> None:
    """Internal helper to invalidate caches for a given resource type."""
    if resource_type == "knowledge":
        knowledge_stats_cache.clear()
        search_cache.delete_pattern("knowledge_search:")
    elif resource_type == "vector":
        vector_stats_cache.clear()
    elif resource_type == "search":
        search_cache.delete_pattern("unified_search:")
    # Also clear list caches
    list_key = cache_key(resource_type, "list")
    search_cache.delete(list_key)
    logger.debug("Cache invalidated for resource type: %s", resource_type)


def get_all_cache_stats() -> dict:
    """Return stats for all cache instances."""
    return {
        "vector_stats": vector_stats_cache.stats(),
        "presets": presets_cache.stats(),
        "knowledge_stats": knowledge_stats_cache.stats(),
        "search": search_cache.stats(),
    }
