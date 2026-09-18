"""Test: MemoryCodeCache — 进程级权限码缓存（权限包 src/api/v3/core/permission）

覆盖场景：
  1. 基本 set / get
  2. 未命中返回 None
  3. TTL 自动过期
  4. LRU 淘汰
  5. invalidate（单个 / 全部）
  6. 并发安全（asyncio.Lock）
  7. hit/miss 统计

与旧 `_MemoryCache` 的**有意语义差异**：现在**空集合也会被缓存** ——
用户确实没有权限时反复回源查库没有意义，而权限变更由 `invalidate_*` 主动清理，
不存在"长期脏缓存"。
"""

import asyncio

import pytest

from src.api.v3.core.permission.cache import MemoryCodeCache


@pytest.fixture
def cache() -> MemoryCodeCache:
    return MemoryCodeCache(ttl=2, maxsize=100)


@pytest.mark.asyncio
async def test_set_and_get(cache: MemoryCodeCache):
    await cache.set(1, frozenset({"article:view", "article:create"}))
    assert await cache.get(1) == frozenset({"article:view", "article:create"})


@pytest.mark.asyncio
async def test_get_missing_returns_none(cache: MemoryCodeCache):
    assert await cache.get(99999) is None


@pytest.mark.asyncio
async def test_empty_set_is_cached(cache: MemoryCodeCache):
    """空集合会被缓存（语义变更：避免无权限用户反复回源）"""
    await cache.set(2, frozenset())
    assert await cache.get(2) == frozenset()


@pytest.mark.asyncio
async def test_ttl_expiry():
    cache = MemoryCodeCache(ttl=1, maxsize=10)
    await cache.set(1, frozenset({"a:b"}))
    assert await cache.get(1) is not None
    await asyncio.sleep(1.1)
    assert await cache.get(1) is None


@pytest.mark.asyncio
async def test_lru_eviction():
    cache = MemoryCodeCache(ttl=60, maxsize=2)
    await cache.set(1, frozenset({"a"}))
    await cache.set(2, frozenset({"b"}))
    await cache.set(3, frozenset({"c"}))  # 触发淘汰最早写入的 1
    assert await cache.get(1) is None
    assert await cache.get(3) == frozenset({"c"})


@pytest.mark.asyncio
async def test_invalidate_single(cache: MemoryCodeCache):
    await cache.set(1, frozenset({"a"}))
    assert await cache.invalidate(1) == 1
    assert await cache.get(1) is None
    # 再次失效（已不存在）返回 0
    assert await cache.invalidate(1) == 0


@pytest.mark.asyncio
async def test_invalidate_all(cache: MemoryCodeCache):
    await cache.set(1, frozenset({"a"}))
    await cache.set(2, frozenset({"b"}))
    assert await cache.invalidate(None) == 2
    assert await cache.get(1) is None
    assert await cache.get(2) is None


@pytest.mark.asyncio
async def test_concurrent_access(cache: MemoryCodeCache):
    await asyncio.gather(*(cache.set(index, frozenset({f"p:{index}"})) for index in range(20)))
    results = await asyncio.gather(*(cache.get(index) for index in range(20)))
    assert all(result is not None for result in results)


@pytest.mark.asyncio
async def test_stats(cache: MemoryCodeCache):
    await cache.set(1, frozenset({"a"}))
    await cache.get(1)  # hit
    await cache.get(2)  # miss

    stats = cache.stats()
    assert stats["size"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
    assert "ttl" in stats and "maxsize" in stats
