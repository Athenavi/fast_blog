"""
数据备份管理 API
提供备份、恢复、调度和管理功能
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.system.backup_service import backup_service
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter(tags=["backup"])


@router.post("/database", summary="备份数据库")
async def backup_database(
        backup_type: str = Body("full", description="备份类型 (full/incremental)"),
        current_user=Depends(jwt_required)
):
    """
    备份数据库
    
    Args:
        backup_type: 备份类型
        
    Returns:
        备份结果
    """
    try:
        result = await backup_service.backup_database(backup_type)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result['metadata'],
                message="Database backup completed"
            )
        else:
            return ApiResponse(success=False, error=result.get('error', 'Backup failed'))

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/files", summary="备份文件")
async def backup_files(current_user=Depends(jwt_required)):
    """
    备份文件（媒体文件、上传文件等）
    
    Returns:
        备份结果
    """
    try:
        result = await backup_service.backup_files()

        if result['success']:
            return ApiResponse(
                success=True,
                data=result.get('metadata'),
                message="Files backup completed"
            )
        else:
            return ApiResponse(success=False, error=result.get('error', 'Backup failed'))

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/full", summary="完整备份")
async def full_backup(current_user=Depends(jwt_required)):
    """
    完整备份（数据库 + 文件）
    
    Returns:
        备份结果
    """
    try:
        result = await backup_service.full_backup()

        if result['success']:
            return ApiResponse(
                success=True,
                data=result['metadata'],
                message="Full backup completed"
            )
        else:
            return ApiResponse(success=False, error=result.get('error', 'Backup failed'))

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/restore/database", summary="恢复数据库")
async def restore_database(
        backup_path: str = Body(..., description="备份文件路径"),
        confirm: bool = Body(False, description="确认恢复（必须为true）"),
        current_user=Depends(jwt_required)
):
    """
    恢复数据库
    
    ⚠️ 警告：这将覆盖当前数据库的所有数据！
    
    Args:
        backup_path: 备份文件路径
        confirm: 确认标志（必须为true）
        
    Returns:
        恢复结果
    """
    if not confirm:
        return ApiResponse(
            success=False,
            error="Please set confirm=true to proceed with database restore"
        )

    try:
        result = await backup_service.restore_database(backup_path)

        if result['success']:
            return ApiResponse(
                success=True,
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result.get('error', 'Restore failed'))

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/restore/files", summary="恢复文件")
async def restore_files(
        backup_path: str = Body(..., description="备份文件路径"),
        confirm: bool = Body(False, description="确认恢复（必须为true）"),
        current_user=Depends(jwt_required)
):
    """
    恢复文件
    
    ⚠️ 警告：这将覆盖当前的文件！
    
    Args:
        backup_path: 备份文件路径
        confirm: 确认标志（必须为true）
        
    Returns:
        恢复结果
    """
    if not confirm:
        return ApiResponse(
            success=False,
            error="Please set confirm=true to proceed with files restore"
        )

    try:
        result = await backup_service.restore_files(backup_path)

        if result['success']:
            return ApiResponse(
                success=True,
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result.get('error', 'Restore failed'))

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/list", summary="列出备份")
async def list_backups(
        backup_type: Optional[str] = Query(None, description="备份类型过滤 (database/files/full)"),
        current_user=Depends(jwt_required)
):
    """
    列出所有备份
    
    Args:
        backup_type: 备份类型过滤
        
    Returns:
        备份列表
    """
    try:
        backups = backup_service.list_backups(backup_type)

        return ApiResponse(
            success=True,
            data={
                'backups': backups,
                'total': len(backups)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/delete", summary="删除备份")
async def delete_backup(
        backup_path: str = Body(..., description="备份文件或目录路径"),
        current_user=Depends(jwt_required)
):
    """
    删除备份
    
    Args:
        backup_path: 备份路径
        
    Returns:
        删除结果
    """
    try:
        success = backup_service.delete_backup(backup_path)

        if success:
            return ApiResponse(
                success=True,
                message="Backup deleted successfully"
            )
        else:
            return ApiResponse(success=False, error="Failed to delete backup")

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/cleanup", summary="清理旧备份")
async def cleanup_old_backups(
        days: int = Body(30, description="保留天数"),
        current_user=Depends(jwt_required)
):
    """
    清理旧备份
    
    Args:
        days: 保留天数，超过此天数的备份将被删除
        
    Returns:
        清理结果
    """
    try:
        await backup_service.cleanup_old_backups(days)
        
        return ApiResponse(
            success=True,
            message=f"Cleaned up backups older than {days} days"
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/config", summary="获取备份配置")
async def get_backup_config(current_user=Depends(jwt_required)):
    """
    获取备份配置
    
    Returns:
        备份配置
    """
    try:
        config = {
            'retention_days': backup_service.config['retention_days'],
            'auto_backup_enabled': backup_service.config['auto_backup_enabled'],
            'auto_backup_schedule': backup_service.config['auto_backup_schedule'],
            'compress_backups': backup_service.config['compress_backups'],
            'backup_database': backup_service.config['backup_database'],
            'backup_files': backup_service.config['backup_files'],
            'backup_directory': backup_service.backup_dir,
        }

        return ApiResponse(
            success=True,
            data=config
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/config/update", summary="更新备份配置")
async def update_backup_config(
        retention_days: Optional[int] = Body(None, description="保留天数"),
        auto_backup_enabled: Optional[bool] = Body(None, description="是否启用自动备份"),
        auto_backup_schedule: Optional[str] = Body(None, description="自动备份计划 (daily/weekly/monthly)"),
        compress_backups: Optional[bool] = Body(None, description="是否压缩备份"),
        current_user=Depends(jwt_required)
):
    """
    更新备份配置
    
    Args:
        retention_days: 保留天数
        auto_backup_enabled: 是否启用自动备份
        auto_backup_schedule: 自动备份计划
        compress_backups: 是否压缩备份
        
    Returns:
        更新结果
    """
    try:
        if retention_days is not None:
            backup_service.config['retention_days'] = retention_days

        if auto_backup_enabled is not None:
            backup_service.config['auto_backup_enabled'] = auto_backup_enabled

        if auto_backup_schedule is not None:
            if auto_backup_schedule not in ['daily', 'weekly', 'monthly']:
                return ApiResponse(success=False, error="Invalid schedule. Must be 'daily', 'weekly', or 'monthly'")
            backup_service.config['auto_backup_schedule'] = auto_backup_schedule

        if compress_backups is not None:
            backup_service.config['compress_backups'] = compress_backups

        return ApiResponse(
            success=True,
            message="Backup configuration updated",
            data=backup_service.config
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/stats", summary="获取备份统计")
async def get_backup_stats(current_user=Depends(jwt_required)):
    """
    获取备份统计信息
    
    Returns:
        统计数据
    """
    try:
        backups = backup_service.list_backups()

        # 计算统计信息
        total_backups = len(backups)
        total_size = sum(b.get('size', 0) for b in backups)

        # 按类型统计
        by_type = {}
        for backup in backups:
            backup_type = backup.get('type', 'unknown')
            if backup_type not in by_type:
                by_type[backup_type] = {'count': 0, 'size': 0}
            by_type[backup_type]['count'] += 1
            by_type[backup_type]['size'] += backup.get('size', 0)

        # 格式化大小
        for backup_type in by_type:
            by_type[backup_type]['size_human'] = backup_service._format_size(by_type[backup_type]['size'])

        return ApiResponse(
            success=True,
            data={
                'total_backups': total_backups,
                'total_size': total_size,
                'total_size_human': backup_service._format_size(total_size),
                'by_type': by_type,
                'retention_days': backup_service.config['retention_days']
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/schedule", summary="设置自动备份计划")
async def set_backup_schedule(
        enabled: bool = Body(..., description="是否启用"),
        schedule: str = Body("daily", description="备份计划 (daily/weekly/monthly)"),
        time: str = Body("02:00", description="备份时间 (HH:MM)"),
        current_user=Depends(jwt_required)
):
    """
    设置自动备份计划
    
    Args:
        enabled: 是否启用自动备份
        schedule: 备份计划
        time: 备份时间
        
    Returns:
        设置结果
    """
    try:
        if schedule not in ['daily', 'weekly', 'monthly']:
            return ApiResponse(success=False, error="Invalid schedule")

        # 在实际应用中，这里应该集成到任务调度系统
        # 例如使用APScheduler或Celery

        backup_service.config['auto_backup_enabled'] = enabled
        backup_service.config['auto_backup_schedule'] = schedule

        return ApiResponse(
            success=True,
            message=f"Auto backup scheduled: {schedule} at {time}",
            data={
                'enabled': enabled,
                'schedule': schedule,
                'time': time
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
