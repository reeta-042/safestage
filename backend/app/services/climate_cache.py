"""
In-memory TTL cache for FortyGuard API responses.

Prevents duplicate API calls for the same event location and time period.
Cache key: (endpoint, latitude, longitude, date, time)
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClimateCache:
    """Simple in-memory TTL cache for FortyGuard climate responses."""

    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _make_key(cls, endpoint: str, **params) -> str:
        """Create a deterministic cache key from endpoint + parameters."""
        # Round lat/lon to 4 decimal places (~11m precision) to improve cache hits
        normalized = {
            "endpoint": endpoint,
            **{k: round(v, 4) if isinstance(v, float) else v for k, v in sorted(params.items())}
        }
        raw = json.dumps(normalized, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def get(cls, endpoint: str, **params) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if it exists and hasn't expired."""
        key = cls._make_key(endpoint, **params)
        entry = cls._cache.get(key)
        if entry is None:
            return None

        ttl = getattr(settings, 'CLIMATE_CACHE_TTL_SECONDS', 3600)
        if time.time() - entry["timestamp"] > ttl:
            del cls._cache[key]
            logger.debug(f"Cache expired for {endpoint}")
            return None

        logger.info(f"Cache HIT for {endpoint} (key={key[:12]}...)")
        return entry["data"]

    @classmethod
    def set(cls, endpoint: str, data: Dict[str, Any], **params) -> None:
        """Store a response in the cache."""
        key = cls._make_key(endpoint, **params)
        cls._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        logger.debug(f"Cached response for {endpoint} (key={key[:12]}...)")

    @classmethod
    def invalidate(cls, endpoint: str = None, **params) -> None:
        """Remove specific or all cached entries."""
        if endpoint is None:
            cls._cache.clear()
            logger.info("Climate cache cleared entirely")
            return
        key = cls._make_key(endpoint, **params)
        cls._cache.pop(key, None)

    @classmethod
    def stats(cls) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        ttl = getattr(settings, 'CLIMATE_CACHE_TTL_SECONDS', 3600)
        now = time.time()
        valid = sum(1 for e in cls._cache.values() if now - e["timestamp"] <= ttl)
        return {
            "total_entries": len(cls._cache),
            "valid_entries": valid,
            "expired_entries": len(cls._cache) - valid,
            "ttl_seconds": ttl
        }
