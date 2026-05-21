"""
备份管理 API - V2 版本
提供自动化的数据库和文件备份、恢复功能
"""
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks

from shared.models.user import User
from shared.services.system.backup_service import BackupService
from src.api.v1.core.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(prefix="/backup", tags=["Backup Management"])

# 初始化备份服务
backup_service = BackupService()


@router.post("/database", summary="备份数据库")
async def backup_database(
        background_tasks: BackgroundTasks,
        backup_type: str = 'full',
        current_user: User = Depends(jwt_required)
):
    """
    创建数据库备份
    
    参数:
    - backup_type: 备份类型 ('full' 完整备份 或 'incremental' 增量备份)
    
    返回备份文件信息和元数据
    """
    # 检查权限（需要管理员权限）
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = await backup_service.backup_database(backup_type=backup_type)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result['metadata'],
                message=f"数据库备份成功: {result['metadata']['size_human']}"
            )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '备份失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"备份失败: {str(e)}"
        )


@router.post("/files", summary="备份文件")
async def backup_files(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(jwt_required)
):
    """
    创建文件备份（媒体文件、上传文件等）
    
    备份内容包括:
    - media/ 目录
    - upload_chunks/ 目录
    - static/ 目录
    - themes/ 目录
    - plugins/ 目录
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = await backup_service.backup_files()

        if result['success']:
            if result.get('backup_path'):
                return ApiResponse(
                    success=True,
                    data=result.get('metadata', {}),
                    message=f"文件备份成功: {result['metadata'].get('size_human', 'N/A')}"
                )
            else:
                return ApiResponse(
                    success=True,
                    data={},
                    message="没有需要备份的文件"
                )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '备份失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"备份失败: {str(e)}"
        )


@router.post("/full", summary="完整备份")
async def backup_full(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(jwt_required)
):
    """
    创建完整备份（数据库 + 文件）
    
    这是最全面的备份方式，建议定期执行
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = await backup_service.backup_full()

        if result['success']:
            return ApiResponse(
                success=True,
                data=result.get('metadata', {}),
                message="完整备份成功"
            )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '备份失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"备份失败: {str(e)}"
        )


@router.get("/list", summary="列出所有备份")
async def list_backups(
        backup_type: Optional[str] = None,
        limit: int = 50,
        current_user: User = Depends(jwt_required)
):
    """
    列出所有备份文件
    
    参数:
    - backup_type: 过滤备份类型 ('database', 'files', 'full')
    - limit: 返回数量限制（默认50）
    
    返回备份列表，按时间倒序排列
    """
    try:
        backups = backup_service.list_backups(backup_type=backup_type, limit=limit)

        return ApiResponse(
            success=True,
            data={
                'backups': backups,
                'total': len(backups),
                'backup_types': {
                    'database': sum(1 for b in backups if b.get('type') == 'database'),
                    'files': sum(1 for b in backups if b.get('type') == 'files'),
                    'full': sum(1 for b in backups if b.get('type') == 'full'),
                }
            }
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"获取备份列表失败: {str(e)}"
        )


@router.post("/restore/database", summary="恢复数据库")
async def restore_database(
        backup_file: str,
        current_user: User = Depends(jwt_required)
):
    """
    从备份文件恢复数据库
    
    ⚠️ 警告: 此操作会覆盖当前数据库，请谨慎使用！
    
    参数:
    - backup_file: 备份文件路径或文件名
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = await backup_service.restore_database(backup_file)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result.get('metadata', {}),
                message="数据库恢复成功"
            )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '恢复失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"恢复失败: {str(e)}"
        )


@router.post("/restore/files", summary="恢复文件")
async def restore_files(
        backup_file: str,
        current_user: User = Depends(jwt_required)
):
    """
    从备份文件恢复文件
    
    ⚠️ 警告: 此操作会覆盖当前文件，请谨慎使用！
    
    参数:
    - backup_file: 备份文件路径或文件名
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = await backup_service.restore_files(backup_file)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result.get('metadata', {}),
                message="文件恢复成功"
            )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '恢复失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"恢复失败: {str(e)}"
        )


@router.delete("/{backup_id}", summary="删除备份")
async def delete_backup(
        backup_id: str,
        current_user: User = Depends(jwt_required)
):
    """
    删除指定的备份文件
    
    参数:
    - backup_id: 备份文件ID或文件名
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = backup_service.delete_backup(backup_id)

        if result['success']:
            return ApiResponse(
                success=True,
                message="备份删除成功"
            )
        else:
            return ApiResponse(
                success=False,
                error=result.get('error', '删除失败')
            )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"删除失败: {str(e)}"
        )


@router.get("/schedule", summary="获取备份计划")
async def get_backup_schedule(
        current_user: User = Depends(jwt_required)
):
    """
    获取自动备份计划配置
    
    返回当前的备份计划和设置
    """
    try:
        schedule = backup_service.get_backup_schedule()

        return ApiResponse(
            success=True,
            data=schedule
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"获取备份计划失败: {str(e)}"
        )


@router.post("/schedule", summary="更新备份计划")
async def update_backup_schedule(
        auto_backup_enabled: bool,
        auto_backup_schedule: str = 'daily',
        retention_days: int = 30,
        compress_backups: bool = True,
        current_user: User = Depends(jwt_required)
):
    """
    更新自动备份计划配置
    
    参数:
    - auto_backup_enabled: 是否启用自动备份
    - auto_backup_schedule: 备份频率 ('hourly', 'daily', 'weekly', 'monthly')
    - retention_days: 备份保留天数
    - compress_backups: 是否压缩备份文件
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        config = {
            'auto_backup_enabled': auto_backup_enabled,
            'auto_backup_schedule': auto_backup_schedule,
            'retention_days': retention_days,
            'compress_backups': compress_backups,
        }

        backup_service.update_backup_schedule(config)

        return ApiResponse(
            success=True,
            data=config,
            message="备份计划更新成功"
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"更新备份计划失败: {str(e)}"
        )


@router.get("/stats", summary="获取备份统计")
async def get_backup_stats(
        current_user: User = Depends(jwt_required)
):
    """
    获取备份统计信息
    
    返回备份总数、总大小、最新备份时间等
    """
    try:
        stats = backup_service.get_backup_stats()

        return ApiResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"获取统计信息失败: {str(e)}"
        )


@router.post("/cleanup", summary="清理过期备份")
async def cleanup_old_backups(
        days_to_keep: Optional[int] = None,
        current_user: User = Depends(jwt_required)
):
    """
    清理过期的备份文件
    
    参数:
    - days_to_keep: 保留天数（可选，默认使用配置的保留天数）
    
    返回被删除的备份列表
    """
    # 检查权限
    if not current_user.is_admin():
        return ApiResponse(
            success=False,
            error="需要管理员权限"
        )

    try:
        result = backup_service.cleanup_old_backups(days_to_keep=days_to_keep)

        return ApiResponse(
            success=True,
            data={
                'deleted_count': result.get('deleted_count', 0),
                'freed_space': result.get('freed_space', 0),
                'freed_space_human': result.get('freed_space_human', '0 B'),
                'deleted_backups': result.get('deleted_backups', [])
            },
            message=f"清理完成，删除 {result.get('deleted_count', 0)} 个备份文件"
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"清理失败: {str(e)}"
        )
