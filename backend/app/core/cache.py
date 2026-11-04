"""Redis access plus a fixed-window rate limiter. Both fail open if Redis is down."""

import logging
from functools import lru_cache
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import get_settings

log = logging.getLogger(__name__)


class KeyValueStore(Protocol):
    async def incr(self, name: str) -> int: ...
    async def expire(self, name: str, time: int) -> object: ...
    async def get(self, name: str) -> object: ...
    async def set(self, name: str, value: str, ex: int | None = None) -> object: ...
    async def ping(self) -> object: ...


@lru_cache
def get_redis() -> KeyValueStore:
    return Redis.from_url(get_settings().redis_url, decode_responses=True, socket_timeout=2)


async def ping_redis(store: KeyValueStore | None = None) -> bool:
    try:
        await (store or get_redis()).ping()
        return True
    except Exception:
        return False


async def hit_rate_limit(
    store: KeyValueStore, key: str, limit: int, window_seconds: int = 60
) -> bool:
    """Count one hit; return True if the caller is over the limit."""
    try:
        count = await store.incr(key)
        if count == 1:
            await store.expire(key, window_seconds)
        return count > limit
    except Exception as exc:  # Redis down: do not block users
        log.warning("rate limiter unavailable: %s", exc)
        return False
