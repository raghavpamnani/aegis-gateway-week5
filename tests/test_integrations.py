"""Opt-in real integration checks; skips are reported, never counted as validation."""

import os

import pytest

from aegis.cache import ResponseCache
from aegis.config import Settings
from aegis.store import Store


@pytest.mark.asyncio
async def test_real_redis_vector_search_and_isolation(tmp_path):
    url = os.getenv("AEGIS_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set AEGIS_TEST_REDIS_URL to test actual Redis Search")
    s = Settings(home=tmp_path, redis_url=url)
    cache = ResponseCache(Store(tmp_path), s)
    # Unique scope avoids clobbering application data.
    import hashlib

    scope = hashlib.sha256(str(tmp_path).encode()).hexdigest()
    try:
        await cache.put(scope, [1.0, 0.0, 0.0], {"answer": "checked"})
        hit = await cache.get(scope, [0.9999, 0.001, 0.0])
        assert hit and hit[0]["answer"] == "checked"
        assert await cache.get("0" * 64, [1.0, 0.0, 0.0]) is None
        assert await cache.get(scope, [0.0, 1.0, 0.0]) is None
    finally:
        await cache.close()
