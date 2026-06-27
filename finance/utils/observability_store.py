"""Redis access for observability counters (celery-observability T02–T04)."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import redis
from django.conf import settings


@lru_cache(maxsize=1)
def get_observability_redis() -> redis.Redis:
    url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=False)


def incr_with_expire(key: str, ttl: int) -> None:
    client = get_observability_redis()
    pipe = client.pipeline()
    pipe.incr(key)
    pipe.expire(key, ttl)
    pipe.execute()


def redis_keys(pattern: str) -> list[str]:
    client = get_observability_redis()
    raw_keys = client.keys(pattern)
    decoded: list[str] = []
    for key in raw_keys:
        decoded.append(key.decode() if isinstance(key, bytes) else key)
    return decoded


def redis_get_int(key: str) -> int:
    client = get_observability_redis()
    value = client.get(key)
    if value is None:
        return 0
    if isinstance(value, bytes):
        value = value.decode()
    return int(value)


def redis_delete(key: str) -> None:
    get_observability_redis().delete(key)


def redis_delete_many(keys: Iterable[str]) -> None:
    key_list = list(keys)
    if not key_list:
        return
    get_observability_redis().delete(*key_list)


def clear_observability_redis_cache() -> None:
    """Test helper — reset cached client after settings override."""
    get_observability_redis.cache_clear()
