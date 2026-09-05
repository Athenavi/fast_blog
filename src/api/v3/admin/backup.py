"""
V3 备份管理 API

权限要求:
  POST   /backup              → backup:create
  POST   /backup/restore      → backup:restore
  DELETE /backup/{backup_id}  → backup:delete

实现说明: 统一委托给 V2 BackupService（真实实现，含备份/恢复/删除），
避免与 V2 重复维护两套备份逻辑，同时修复原先引用不存在的
DatabaseBackup.create_backup/restore_backup 方法导致的 500 与假删除。
"""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.system.backup_service import BackupService
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-backup"])

backup_service = BackupService()


def _resolve_backup_path(ref: str):
    """根据 备份文件名/备份id 从 list_backups 解析真实的备份路径(或全量备份目录)。"""
    for backup in backup_service.list_backups():
        if (
            backup.get("filename") == ref
            or backup.get("path") == ref
            or backup.get("backup_dir") == ref
        ):
            return backup.get("path") or backup.get("backup_dir")
    return None


@router.post("/backup", summary="创建备份")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:create")),
):
    try:
        result = await backup_service.backup_database(backup_type="full")
        if result.get("success"):
            return ApiResponse(success=True, data=result.get("metadata", {}), message="备份创建成功")
        return ApiResponse(success=False, error=result.get("error", "备份失败"))
    except Exception as e:
        logger.exception("V3 backup create failed")
        return ApiResponse(success=False, error=f"备份失败: {e}")


@router.post("/backup/restore", summary="恢复备份")
async def restore_backup(
    filename: str = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:restore")),
):
    try:
        backup_path = _resolve_backup_path(filename)
        if not backup_path:
            return ApiResponse(success=False, error=f"备份不存在: {filename}")
        result = await backup_service.restore_database(backup_path)
        if result.get("success"):
            return ApiResponse(success=True, message="备份恢复成功")
        return ApiResponse(success=False, error=result.get("error", "恢复失败"))
    except Exception as e:
        logger.exception("V3 backup restore failed")
        return ApiResponse(success=False, error=f"恢复失败: {e}")


@router.delete("/backup/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:delete")),
):
    try:
        backup_path = _resolve_backup_path(backup_id)
        if not backup_path:
            return ApiResponse(success=False, error=f"备份不存在: {backup_id}")
        result = backup_service.delete_backup(backup_path)
        if result:
            return ApiResponse(success=True, message="备份已删除")
        return ApiResponse(success=False, error="备份删除失败")
    except Exception as e:
        logger.exception("V3 backup delete failed")
        return ApiResponse(success=False, error=f"删除失败: {e}")
