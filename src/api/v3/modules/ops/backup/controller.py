"""backup 模块路由

::

    GET    /api/v3/ops/backup                备份列表
    POST   /api/v3/ops/backup/database       数据库备份
    POST   /api/v3/ops/backup/incremental    增量 / 差异备份（相对基准的变化表快照）
    POST   /api/v3/ops/backup/files          文件备份
    POST   /api/v3/ops/backup/full           全量备份
    POST   /api/v3/ops/backup/restore        恢复
    GET    /api/v3/ops/backup/chain          恢复链预览（增量要挂在哪些备份后面）
    POST   /api/v3/ops/backup/restore-chain  按恢复链还原（基准 → 增量）
    POST   /api/v3/ops/backup/verify         校验备份完整性
    GET    /api/v3/ops/backup/cloud          云存储配置（密钥不回传）
    PUT    /api/v3/ops/backup/cloud          保存云存储配置（密钥加密落库）
    POST   /api/v3/ops/backup/cloud/upload   上传备份到云存储（S3 / OSS）
    DELETE /api/v3/ops/backup                删除某个备份（?backup_path=）
    POST   /api/v3/ops/backup/cleanup        清理过期备份
    GET    /api/v3/ops/backup/stats          备份统计
    GET    /api/v3/ops/backup/schedule       备份计划
    PUT    /api/v3/ops/backup/schedule       更新备份计划

权限码：``backup:view`` / ``backup:create`` / ``backup:restore`` / ``backup:delete`` /
``backup:cloud``（云存储配置与上传单独授权：目标桶与凭据是敏感配置）
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.backup.schema import (
    BackupPathRequest,
    CloudConfigPayload,
    CloudUploadRequest,
    IncrementalRequest,
    RestoreChainRequest,
    RestoreRequest,
    ScheduleUpdate,
)
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
    _perm=AuthControl(codes.BACKUP_VIEW),
    backup_type: Optional[str] = Query(default=None, description="full / database / files"),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
) -> dict:
    items = await backup_ops_service.list_backups(backup_type=backup_type, limit=limit)
    return resp.success_page(items, len(items), 1, len(items) or 1)


@router.post("/database", response_model=ResponseModel, summary="数据库备份")
async def backup_database(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CREATE),
    backup_type: str = Query(default="full", description="full / schema / data"),
) -> dict:
    return resp.success(await backup_ops_service.create_database_backup(backup_type), msg="备份完成")


@router.post("/files", response_model=ResponseModel, summary="文件备份")
async def backup_files(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CREATE),
) -> dict:
    return resp.success(await backup_ops_service.create_files_backup(), msg="备份完成")


@router.post("/full", response_model=ResponseModel, summary="全量备份")
async def backup_full(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CREATE),
) -> dict:
    return resp.success(await backup_ops_service.create_full_backup(), msg="备份完成")


@router.post("/restore", response_model=ResponseModel, summary="恢复备份")
async def restore_backup(
    payload: RestoreRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_RESTORE),
) -> dict:
    result = await backup_ops_service.restore(payload.backup_file, payload.backup_type)
    return resp.success(result, msg="恢复完成")


# ---------------------------------------------------------------- 增量 / 差异备份
@router.post("/incremental", response_model=ResponseModel, summary="创建增量 / 差异备份")
async def backup_incremental(
    payload: IncrementalRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CREATE),
) -> dict:
    """只导出「相对基准发生变化」的表的数据（结构由基准备份提供）。"""
    result = await backup_ops_service.create_incremental(
        base_path=payload.base_path,
        tables=payload.tables,
        differential=payload.differential,
    )
    msg = "无变化，已跳过" if result.get("skipped") else "增量备份完成"
    return resp.success(result, msg=msg)


@router.get("/chain", response_model=ResponseModel, summary="恢复链预览")
async def backup_chain(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_VIEW),
    backup_path: str = Query(description="增量 / 差异备份的路径或文件名"),
) -> dict:
    """增量 / 差异备份还原时要先走这些前置备份（基准在前、目标在后）。"""
    return resp.success(await backup_ops_service.chain_plan(backup_path))


@router.post("/restore-chain", response_model=ResponseModel, summary="按恢复链还原")
async def restore_backup_chain(
    payload: RestoreChainRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_RESTORE),
) -> dict:
    result = await backup_ops_service.restore_chain(
        payload.backup_path, truncate=payload.truncate
    )
    return resp.success(result, msg="已按恢复链还原")


# ---------------------------------------------------------------- 校验
@router.post("/verify", response_model=ResponseModel, summary="校验备份完整性")
async def verify_backup(
    payload: BackupPathRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_VIEW),
) -> dict:
    """真读文件：sha256 比对 + 归档可读 + ``pg_restore --list``，逐项给出结论。"""
    result = await backup_ops_service.verify(payload.backup_path)
    return resp.success(result, msg="校验完成")


# ---------------------------------------------------------------- 云存储
@router.get("/cloud", response_model=ResponseModel, summary="云存储配置")
async def get_cloud_config(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_VIEW),
) -> dict:
    """密钥永不回传，只回 ``has_secret``。"""
    return resp.success(await backup_ops_service.cloud_config(db))


@router.put("/cloud", response_model=ResponseModel, summary="保存云存储配置")
async def save_cloud_config(
    payload: CloudConfigPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CLOUD),
) -> dict:
    return resp.success(await backup_ops_service.save_cloud_config(db, payload), msg="已保存")


@router.post("/cloud/upload", response_model=ResponseModel, summary="上传备份到云存储")
async def upload_backup_to_cloud(
    payload: CloudUploadRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CLOUD),
) -> dict:
    """真实上传到 S3 / OSS；未配置、凭据坏掉、云端拒绝都会带回原因。"""
    result = await backup_ops_service.upload_to_cloud(db, payload.backup_path)
    return resp.success(result, msg="已上传到云端")


@router.post("/cleanup", response_model=ResponseModel, summary="清理过期备份")
async def cleanup_backups(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_DELETE),
    days_to_keep: Optional[int] = Query(default=None, ge=1, le=3650),
) -> dict:
    return resp.success(await backup_ops_service.cleanup(days_to_keep), msg="清理完成")


@router.get("/stats", response_model=ResponseModel, summary="备份统计")
async def backup_stats(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_VIEW),
) -> dict:
    return resp.success(await backup_ops_service.stats())


@router.get("/schedule", response_model=ResponseModel, summary="备份计划")
async def get_schedule(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_VIEW),
) -> dict:
    return resp.success(await backup_ops_service.schedule())


@router.put("/schedule", response_model=ResponseModel, summary="更新备份计划")
async def update_schedule(
    payload: ScheduleUpdate,
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_CREATE),
) -> dict:
    config = payload.model_dump(exclude_unset=True)
    return resp.success(await backup_ops_service.update_schedule(config), msg="已保存")


@router.delete("", response_model=ResponseModel, summary="删除某个备份")
async def delete_backup(
    _current: CurrentUser,
    _perm=AuthControl(codes.BACKUP_DELETE),
    backup_path: str = Query(description="备份文件路径（来自列表的 path 字段）"),
) -> dict:
    deleted = await backup_ops_service.delete_backup(backup_path)
    return resp.success({"deleted": deleted}, msg="已删除" if deleted else "未找到该备份")
