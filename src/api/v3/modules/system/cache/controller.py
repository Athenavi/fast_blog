"""cache 模块路由（系统级缓存管理）

RESTful 主路径：

    GET    /api/v3/system/cache/stats           多级缓存 + 权限缓存统计
    POST   /api/v3/system/cache/clear           清空全部缓存层
    POST   /api/v3/system/cache/warmup          批量预热
    GET    /api/v3/system/cache/items/{key}     读取单个键
    PUT    /api/v3/system/cache/items/{key}     写入单个键
    DELETE /api/v3/system/cache/items/{key}     删除单个键

本模块**无数据库表**，因此不需要 ``db`` 依赖（同 ``health`` 模块）。

权限码：``module_system:cache:view`` / ``:clear`` / ``:warmup`` / ``:write``；
写操作经 ``OperationLogRoute`` 落审计日志。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.cache.schema import CacheItemUpsert, CacheWarmupPayload
from src.api.v3.modules.system.cache.service import cache_admin_service

router = APIRouter(prefix="/cache", tags=["system-cache"], route_class=OperationLogRoute)


@router.get("/stats", response_model=ResponseModel, summary="缓存统计")
async def cache_stats(
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_VIEW),
) -> dict:
    """多级缓存（memory / redis / file）与权限缓存的统计信息"""
    return resp.success(cache_admin_service.stats())


@router.post("/clear", response_model=ResponseModel, summary="清空全部缓存")
async def clear_cache(
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_CLEAR),
) -> dict:
    """清空 L1 / L2 / L3 全部缓存（危险操作，已写审计日志）"""
    await cache_admin_service.clear()
    return resp.success(data=None, msg="缓存已清空")


@router.post("/warmup", response_model=ResponseModel, summary="批量预热缓存")
async def warmup_cache(
    payload: CacheWarmupPayload,
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_WARMUP),
) -> dict:
    """按 ``{"items": [{"key": ..., "value": ..., "ttl": ...}]}`` 批量写入缓存"""
    count = await cache_admin_service.warmup(payload.items)
    return resp.success(data={"warmed": count}, msg=f"已预热 {count} 条")


@router.get("/items/{key}", response_model=ResponseModel, summary="读取缓存键")
async def get_cache_item(
    key: str,
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_VIEW),
) -> dict:
    value = await cache_admin_service.get(key)
    if value is None:
        return resp.fail("缓存键不存在", code=resp.CODE_NOT_FOUND)
    return resp.success(data={"key": key, "value": value})


@router.put("/items/{key}", response_model=ResponseModel, summary="写入缓存键")
async def set_cache_item(
    key: str,
    payload: CacheItemUpsert,
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_WRITE),
) -> dict:
    await cache_admin_service.set(key, payload.value, payload.ttl)
    return resp.success(data={"key": key}, msg="已写入")


@router.delete("/items/{key}", response_model=ResponseModel, summary="删除缓存键")
async def delete_cache_item(
    key: str,
    _current: CurrentUser,
    _perm=AuthControl(codes.CACHE_WRITE),
) -> dict:
    await cache_admin_service.delete(key)
    return resp.success(data=None, msg="已删除")
