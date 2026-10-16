"""cache 模块的业务逻辑

不依赖任何业务表：读写直接走共享服务
``shared/services/core/multi_level_cache.py``（L1 memory → L2 redis → L3 file）。

权限缓存的统计来自 v3 原有能力 ``core/permission/invalidate.py::cache_stats``
（先前只通过 ``/system/permission/cache-stats`` 暴露），这里汇总到同一个面板上展示。
"""

from typing import Any, Dict, List, Optional

from shared.services.core.multi_level_cache import multi_level_cache

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.invalidate import cache_stats as permission_cache_stats

logger = get_logger("cache-admin")


class CacheAdminService:
    """系统级缓存管理服务"""

    def stats(self) -> Dict[str, Any]:
        """汇总多级缓存与权限缓存的统计。

        两部分各自 try/except：任一失败只在该分组里标 error，
        不让整个「缓存管理」页因为一个子系统异常而 500。
        """
        payload: Dict[str, Any] = {"multi_level": {}, "permission": {}}

        try:
            payload["multi_level"] = multi_level_cache.get_stats()
        except Exception as exc:  # noqa: BLE001 - 统计失败不应影响页面
            logger.error("多级缓存统计失败：%s", exc)
            payload["multi_level"] = {"error": type(exc).__name__}

        try:
            payload["permission"] = permission_cache_stats()
        except Exception as exc:  # noqa: BLE001
            logger.error("权限缓存统计失败：%s", exc)
            payload["permission"] = {"error": type(exc).__name__}

        return payload

    async def clear(self) -> None:
        """清空全部缓存层"""
        await multi_level_cache.clear()

    async def warmup(self, items: List[Any]) -> int:
        """批量预热；``items`` 为 ``CacheWarmupItem`` 列表，返回写入条数"""
        keys_data = [{"key": item.key, "value": item.value, "ttl": item.ttl} for item in items]
        if not keys_data:
            return 0
        await multi_level_cache.warmup(keys_data)
        return len(keys_data)

    async def get(self, key: str) -> Optional[Any]:
        return await multi_level_cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await multi_level_cache.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await multi_level_cache.delete(key)


cache_admin_service = CacheAdminService()
