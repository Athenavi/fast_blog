"""
Test: _MemoryCache — 进程级内存权限缓存

覆盖场景:
  1. 基本 set / get
  2. TTL 自动过期
  3. LRU 淘汰
  4. invalidate 主动失效
  5. 并发安全（asyncio.Lock）
  6. 空值 / 异常输入
"""
import asyncio
import time

import pytest

from src.api.v3._permission import _MemoryCache


@pytest.fixture
def cache():
    return _MemoryCache(max_entries=100, ttl=2)  # 短 TTL 方便测试


@pytest.mark.asyncio
async def test_set_and_get(cache: _MemoryCache):
    """最基本的 set/get"""
    await cache.set(1, {"article:view", "article:create"})
    result = await cache.get(1)
    assert result == {"article:view", "article:create"}


@pytest.mark.asyncio
async def test_get_missing(cache: _MemoryCache):
    """不存在的用户返回 None"""
    result = await cache.get(99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_empty_set_not_cached(cache: _MemoryCache):
    """空集合不会被缓存（set 内部跳过空的 codes）"""
    await cache.set(2, set())
    result = await cache.get(2)
    assert result is None


@pytest.mark.asyncio
async def test_ttl_expiry(cache: _MemoryCache):
    """TTL 过期后 get 返回 None"""
    await cache.set(3, {"article:view"})
    # TTL 为 2 秒，等待 3 秒确保过期
    await asyncio.sleep(3)
    result = await cache.get(3)
    assert result is None


@pytest.mark.asyncio
async def test_invalidate(cache: _MemoryCache):
    """主动失效"""
    await cache.set(4, {"article:view"})
    await cache.invalidate(4)
    result = await cache.get(4)
    assert result is None


@pytest.mark.asyncio
async def test_lru_eviction(cache: _MemoryCache):
    """超出 max_entries 时淘汰最旧条目"""
    for i in range(200):
        await cache.set(i, {f"perm:{i}"})

    stats = await cache.stats()
    # 200 次插入, max=100, 至少应淘汰 100 个
    assert stats["evictions"] >= 99
    assert stats["size"] <= 100


@pytest.mark.asyncio
async def test_concurrent_access():
    """并发 set/get 不抛异常"""
    c = _MemoryCache(max_entries=1000, ttl=10)

    async def worker(uid: int):
        for _ in range(50):
            await c.set(uid, {f"perm:{uid}"})
            await c.get(uid)

    tasks = [worker(i) for i in range(20)]
    await asyncio.gather(*tasks)

    stats = await c.stats()
    assert stats["hits"] > 0


@pytest.mark.asyncio
async def test_stats(cache: _MemoryCache):
    """统计信息正确"""
    await cache.set(10, {"a"})
    await cache.get(10)  # hit
    await cache.get(10)  # hit
    await cache.get(20)  # miss
    await cache.get(30)  # miss

    stats = await cache.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 2
    assert stats["hit_rate"] == 50.0
    assert stats["size"] == 1  # 只成功缓存了 user 10


@pytest.mark.asyncio
async def test_clear(cache: _MemoryCache):
    """清空全部"""
    await cache.set(1, {"a"})
    await cache.set(2, {"b"})
    await cache.clear()
    stats = await cache.stats()
    assert stats["size"] == 0
    assert (await cache.get(1)) is None
    assert (await cache.get(2)) is None
