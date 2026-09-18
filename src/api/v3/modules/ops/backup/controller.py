"""backup 模块路由

::

    GET    /api/v3/ops/backup                备份列表
    POST   /api/v3/ops/backup/database       数据库备份
    POST   /api/v3/ops/backup/files          文件备份
    POST   /api/v3/ops/backup/full           全量备份
    POST   /api/v3/ops/backup/restore        恢复
    DELETE /api/v3/ops/backup                删除某个备份（?backup_path=）
    POST   /api/v3/ops/backup/cleanup        清理过期备份
    GET    /api/v3/ops/backup/stats          备份统计
    GET    /api/v3/ops/backup/schedule       备份计划
    PUT    /api/v3/ops/backup/schedule       更新备份计划

权限码：``backup:create`` / ``backup:restore`` / ``backup:delete`` / ``settings:view`` / ``settings:edit``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.backup.schema import RestoreRequest, ScheduleUpdate
from src.api.v3.modules.ops.backup.service import backup_ops_service

router = APIRouter(prefix="/backup", tags=["ops-backup"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="备份列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 备份列表",
)
async def list_backups(
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
    backup_type: Optional[str] = Query(default=None, description="full / database / files"),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
) -> dict:
    items = await backup_ops_service.list_backups(backup_type=backup_type, limit=limit)
    return resp.success_page(items, len(items), 1, len(items) or 1)


@router.post("/database", response_model=ResponseModel, summary="数据库备份")
async def backup_database(
    _current: CurrentUser,
    _perm=AuthControl("backup:create"),
    backup_type: str = Query(default="full", description="full / schema / data"),
) -> dict:
    return resp.success(await backup_ops_service.create_database_backup(backup_type), msg="备份完成")


@router.post("/files", response_model=ResponseModel, summary="文件备份")
async def backup_files(
    _current: CurrentUser,
    _perm=AuthControl("backup:create"),
) -> dict:
    return resp.success(await backup_ops_service.create_files_backup(), msg="备份完成")


@router.post("/full", response_model=ResponseModel, summary="全量备份")
async def backup_full(
    _current: CurrentUser,
    _perm=AuthControl("backup:create"),
) -> dict:
    return resp.success(await backup_ops_service.create_full_backup(), msg="备份完成")


@router.post("/restore", response_model=ResponseModel, summary="恢复备份")
async def restore_backup(
    payload: RestoreRequest,
    _current: CurrentUser,
    _perm=AuthControl("backup:restore"),
) -> dict:
    result = await backup_ops_service.restore(payload.backup_file, payload.backup_type)
    return resp.success(result, msg="恢复完成")


@router.post("/cleanup", response_model=ResponseModel, summary="清理过期备份")
async def cleanup_backups(
    _current: CurrentUser,
    _perm=AuthControl("backup:delete"),
    days_to_keep: Optional[int] = Query(default=None, ge=1, le=3650),
) -> dict:
    return resp.success(await backup_ops_service.cleanup(days_to_keep), msg="清理完成")


@router.get("/stats", response_model=ResponseModel, summary="备份统计")
async def backup_stats(
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await backup_ops_service.stats())


@router.get("/schedule", response_model=ResponseModel, summary="备份计划")
async def get_schedule(
    _current: CurrentUser,
    _perm=AuthControl("settings:view"),
) -> dict:
    return resp.success(await backup_ops_service.schedule())


@router.put("/schedule", response_model=ResponseModel, summary="更新备份计划")
async def update_schedule(
    payload: ScheduleUpdate,
    _current: CurrentUser,
    _perm=AuthControl("settings:edit"),
) -> dict:
    config = payload.model_dump(exclude_unset=True)
    return resp.success(await backup_ops_service.update_schedule(config), msg="已保存")


@router.delete("", response_model=ResponseModel, summary="删除某个备份")
async def delete_backup(
    _current: CurrentUser,
    _perm=AuthControl("backup:delete"),
    backup_path: str = Query(description="备份文件路径（来自列表的 path 字段）"),
) -> dict:
    deleted = await backup_ops_service.delete_backup(backup_path)
    return resp.success({"deleted": deleted}, msg="已删除" if deleted else "未找到该备份")
