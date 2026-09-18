"""权限码缓存层（request.state → 进程内存 LRU → Redis）

保留 fast_blog 既有的三层缓存（比官方"权限集合存会话"更细粒度），并补齐两处缺口：

  1. 失效必须覆盖"内存 + Redis + 跨进程广播"（见 `invalidate.py`）
  2. 缓存键与序列化格式集中在此，避免散落在各处
"""

import asyncio
import time
from collections import OrderedDict
from typing import Any, Dict, FrozenSet, Optional

from src.api.v3.core.logger import get_logger

logger = get_logger("permission.cache")

#: Redis 键前缀与 TTL（与旧实现保持一致，避免灰度期两份缓存）
REDIS_PREFIX = "rbac:perms:"
REDIS_TTL = 300

#: 失效广播频道
INVALIDATE_CHANNEL = "rbac:invalidate"

#: 请求级缓存的属性名（与旧实现一致，便于灰度期共存）
REQUEST_CACHE_ATTR = "_perm_cache"


# ---------------------------------------------------------------- 请求级
def get_request_codes(request: Any) -> Optional[FrozenSet[str]]:
    return getattr(getattr(request, "state", None), REQUEST_CACHE_ATTR, None)


def set_request_codes(request: Any, codes: FrozenSet[str]) -> None:
    try:
        setattr(request.state, REQUEST_CACHE_ATTR, codes)
    except Exception:  # noqa: BLE001 - 某些上下文（如 WebSocket）可能没有 state
        logger.debug("设置请求级权限缓存失败，忽略")


# ---------------------------------------------------------------- 进程内存（TTL + LRU）
class MemoryCodeCache:
    """进程级权限码缓存

    - TTL 过期（默认 300s）
    - LRU 淘汰（默认上限 20000 条）
    - asyncio.Lock 保证并发安全
    - 命中率统计（便于 `/system/permission/cache-stats` 暴露）
    """

    def __init__(self, ttl: int = REDIS_TTL, maxsize: int = 20000) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._store: "OrderedDict[int, tuple[float, FrozenSet[str]]]" = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

    async def get(self, user_id: int) -> Optional[FrozenSet[str]]:
        async with self._lock:
            entry = self._store.get(user_id)
            if entry is None:
                self._misses += 1
                return None
            expires_at, codes = entry
            if expires_at < time.monotonic():
                self._store.pop(user_id, None)
                self._misses += 1
                return None
            self._store.move_to_end(user_id)
            self._hits += 1
            return codes

    async def set(self, user_id: int, codes: FrozenSet[str], ttl: Optional[int] = None) -> None:
        async with self._lock:
            if len(self._store) >= self._maxsize:
                self._store.popitem(last=False)
            self._store[user_id] = (time.monotonic() + (ttl or self._ttl), codes)

    async def invalidate(self, user_id: Optional[int] = None) -> int:
        """失效单个用户；``None`` 表示清空全部。返回受影响条目数"""
        async with self._lock:
            if user_id is None:
                count = len(self._store)
                self._store.clear()
            else:
                count = 1 if self._store.pop(user_id, None) is not None else 0
            self._invalidations += count
            return count

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "maxsize": self._maxsize,
            "ttl": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total else 0.0,
            "invalidations": self._invalidations,
        }


memory_cache = MemoryCodeCache()

# ---------------------------------------------------------------- Redis
_redis_singleton: Any = None
_redis_resolved = False


def get_redis() -> Any:
    """获取共享 Redis 客户端（复用 `redis_service` 单例；不可用时返回 None 并降级）"""
    global _redis_singleton, _redis_resolved
    if not _redis_resolved:
        _redis_resolved = True
        try:
            from src.services.redis_service import redis_service

            _redis_singleton = redis_service
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 不可用，权限缓存降级为进程内存：%s", exc)
            _redis_singleton = None
    return _redis_singleton


def reset_redis_singleton() -> None:
    """测试用：重置 Redis 单例解析状态"""
    global _redis_singleton, _redis_resolved
    _redis_singleton = None
    _redis_resolved = False


def _decode(raw: Any) -> FrozenSet[str]:
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        return frozenset(part for part in raw.split(",") if part)
    if isinstance(raw, (list, tuple, set, frozenset)):
        return frozenset(str(part) for part in raw if part)
    return frozenset({str(raw)})


async def redis_get_codes(user_id: int) -> Optional[FrozenSet[str]]:
    redis = get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(f"{REDIS_PREFIX}{user_id}")
        return None if raw is None else _decode(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 读取权限缓存失败 user=%s：%s", user_id, exc)
        return None


async def redis_set_codes(user_id: int, codes: FrozenSet[str]) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.set(
            f"{REDIS_PREFIX}{user_id}",
            ",".join(sorted(codes)),
            expire=REDIS_TTL,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 写入权限缓存失败 user=%s：%s", user_id, exc)


async def redis_delete_codes(user_id: int) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.delete(f"{REDIS_PREFIX}{user_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 删除权限缓存失败 user=%s：%s", user_id, exc)


async def redis_publish_invalidate(user_id: Optional[int]) -> None:
    """广播失效：``None`` 表示清空全部（各进程收到后清本进程内存）

    注意：`redis_service` 是封装类，**原生客户端在 `.redis` 属性上**；
    这里对两种形态都兼容，避免因封装差异导致广播静默失效。
    """
    redis = get_redis()
    if redis is None:
        return
    client = getattr(redis, "redis", None) or redis
    try:
        await client.publish(INVALIDATE_CHANNEL, "all" if user_id is None else str(user_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("权限缓存失效广播失败：%s", exc)


__all__ = [
    "REDIS_PREFIX",
    "REDIS_TTL",
    "INVALIDATE_CHANNEL",
    "REQUEST_CACHE_ATTR",
    "MemoryCodeCache",
    "memory_cache",
    "get_request_codes",
    "set_request_codes",
    "get_redis",
    "redis_get_codes",
    "redis_set_codes",
    "redis_delete_codes",
    "redis_publish_invalidate",
]
