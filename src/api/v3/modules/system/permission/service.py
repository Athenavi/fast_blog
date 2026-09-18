"""permission 模块业务逻辑

读权限码走 ``capabilities`` 表；求"某用户有哪些权限"走 ``rbac_service``
（与 ``src/api/v3/_permission.py`` 的三重缓存共用同一数据源）。
"""

from collections import defaultdict
from typing import List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.rbac.capability import Capability
from shared.services.security.rbac_service import rbac_service
from src.api.v3._permission import (
    clear_permission_cache,
    get_cache_stats,
    invalidate_permission_cache,
)
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.permission.crud import capability_crud

logger = get_logger("permission")


class PermissionService:
    """权限码查询与校验"""

    async def list_capabilities(
        self,
        db: AsyncSession,
        *,
        resource_type: Optional[str] = None,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Capability], int]:
        return await capability_crud.list(
            db,
            page=1,
            page_size=0,  # 权限码总量有限（当前 ≤ 50），一次性返回便于前端本地过滤
            keyword=keyword,
            filters={"resource_type": resource_type, "is_active": is_active},
            order_by="code",
            order="asc",
        )

    async def grouped(self, db: AsyncSession) -> List[dict]:
        """按 ``resource_type`` 分组返回，供前端权限树/穿梭框使用"""
        caps, _total = await self.list_capabilities(db, is_active=True)
        groups: dict[str, list[dict]] = defaultdict(list)
        for cap in caps:
            groups[cap.resource_type or "other"].append(
                {
                    "id": cap.id,
                    "code": cap.code,
                    "name": cap.name,
                    "description": cap.description,
                    "resource_type": cap.resource_type,
                    "action": cap.action,
                    "is_active": bool(cap.is_active),
                }
            )
        return [
            {"resource_type": resource, "capabilities": items}
            for resource, items in sorted(groups.items())
        ]

    async def user_permissions(self, db: AsyncSession, user_id: int) -> List[str]:
        return sorted(await rbac_service.get_permission_codes_set(db, user_id))

    async def check(self, db: AsyncSession, user_id: int, codes: Sequence[str]) -> dict:
        granted = await rbac_service.get_permission_codes_set(db, user_id)
        result = {code: code in granted for code in codes}
        missing = [code for code, ok in result.items() if not ok]
        return {"granted": result, "all_granted": not missing, "missing": missing}

    async def cache_stats(self) -> dict:
        return await get_cache_stats()

    async def invalidate_cache(self, user_id: Optional[int] = None) -> None:
        """失效权限缓存：传 ``user_id`` 失效单个用户，否则清空全部"""
        if user_id is None:
            await clear_permission_cache()
            logger.info("已清空全部权限缓存")
        else:
            await invalidate_permission_cache(user_id)
            logger.info("已失效用户权限缓存 user_id=%s", user_id)


permission_service = PermissionService()
