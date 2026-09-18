"""权限缓存失效与跨进程广播

设计要点（修的就是审计里的 P1-1）：

  - 失效必须**同时**覆盖：本进程内存、Redis、以及**其它 worker**（广播）
  - 所有权限变更点（角色授权、用户角色变更、角色删除、用户删除…）都应调用 `invalidate_user`
  - 订阅端只清本进程内存（Redis 由失效方删除，避免 N 个进程重复删）

注意 `redis_service` 的原生客户端在其 `.redis` 属性上，两种形态都做兼容。
"""

import asyncio
from typing import Optional

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.cache import (
    INVALIDATE_CHANNEL,
    get_redis,
    memory_cache,
    native_client,
    redis_delete_codes,
    redis_publish_invalidate,
)

logger = get_logger("permission.invalidate")

_subscriber_task: Optional[asyncio.Task] = None
_subscriber_running = False


async def invalidate_user(user_id: int) -> None:
    """失效单个用户的权限缓存（本进程 + Redis + 广播）"""
    await memory_cache.invalidate(user_id)
    await redis_delete_codes(user_id)
    await redis_publish_invalidate(user_id)


async def invalidate_users(user_ids: list[int]) -> None:
    for user_id in user_ids:
        await invalidate_user(user_id)


async def invalidate_all() -> None:
    """清空全部权限缓存（本进程 + 广播；Redis 键靠 TTL 自然过期，避免 KEYS 扫描）"""
    await memory_cache.invalidate(None)
    await redis_publish_invalidate(None)


async def _subscribe_forever() -> None:
    global _subscriber_running

    redis = get_redis()
    client = native_client()
    if client is None:
        logger.info("Redis 不可用，跳过权限缓存失效频道订阅（降级为 TTL 过期）")
        return

    # lifespan 应已建立连接；这里兜底一次
    if getattr(redis, "_redis", None) is None and hasattr(redis, "connect"):
        try:
            await redis.connect()
            client = native_client() or client
        except Exception as exc:  # noqa: BLE001
            logger.info("Redis 未连接，跳过权限失效频道订阅：%s", exc)
            return

    _subscriber_running = True
    try:
        pubsub = client.pubsub()
        await pubsub.subscribe(INVALIDATE_CHANNEL)
        logger.info("已订阅权限缓存失效频道: %s", INVALIDATE_CHANNEL)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = message.get("data")
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode("utf-8", "ignore")
            if payload == "all":
                await memory_cache.invalidate(None)
                continue
            try:
                await memory_cache.invalidate(int(payload))
            except (TypeError, ValueError):
                continue
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        logger.warning("权限缓存失效频道订阅中断", exc_info=True)
    finally:
        _subscriber_running = False


def start_invalidate_subscriber() -> Optional[asyncio.Task]:
    """以后台任务启动失效订阅（幂等，持引用防 GC）"""
    global _subscriber_task
    if _subscriber_task is not None and not _subscriber_task.done():
        return _subscriber_task
    _subscriber_task = asyncio.ensure_future(_subscribe_forever())
    _subscriber_task.set_name("permission_invalidate_subscriber")
    return _subscriber_task


def cache_stats() -> dict:
    """权限缓存统计（供 `/system/permission/cache-stats` 暴露）"""
    redis = get_redis()
    return {
        "memory": memory_cache.stats(),
        "redis": {"available": redis is not None},
        "subscriber_running": _subscriber_running,
    }


__all__ = [
    "invalidate_user",
    "invalidate_users",
    "invalidate_all",
    "start_invalidate_subscriber",
    "cache_stats",
]
