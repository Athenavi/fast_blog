"""
备份管理 API

提供备份的创建、查询、删除等功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.backup_service import backup_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/database", summary="备份数据库", description="创建数据库备份")
async def backup_database(
        compress: bool = Body(True, description="是否压缩"),
        current_user=Depends(jwt_required),
):
    """备份数据库"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = backup_service.create_database_backup(compress=compress)

    if result['status'] == 'completed':
        return ApiResponse(
            success=True,
            message="Database backup created successfully",
            data=result
        )
    else:
        return ApiResponse(
            success=False,
            error=result.get('error', 'Backup failed')
        )


@router.post("/files", summary="备份文件", description="创建文件备份")
async def backup_files(
        source_dirs: Optional[list] = Body(None, description="要备份的目录列表"),
        compress: bool = Body(True, description="是否压缩"),
        current_user=Depends(jwt_required),
):
    """备份文件"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = backup_service.create_files_backup(
        source_dirs=source_dirs,
        compress=compress
    )

    if result['status'] == 'completed':
        return ApiResponse(
            success=True,
            message="Files backup created successfully",
            data=result
        )
    else:
        return ApiResponse(
            success=False,
            error=result.get('error', 'Backup failed')
        )


@router.post("/full", summary="完整备份", description="创建完整备份（数据库+文件）")
async def backup_full(
        include_database: bool = Body(True, description="是否包含数据库"),
        include_files: bool = Body(True, description="是否包含文件"),
        compress: bool = Body(True, description="是否压缩"),
        current_user=Depends(jwt_required),
):
    """完整备份"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = backup_service.create_full_backup(
        include_database=include_database,
        include_files=include_files,
        compress=compress
    )

    if result['status'] == 'completed':
        return ApiResponse(
            success=True,
            message="Full backup created successfully",
            data=result
        )
    else:
        return ApiResponse(
            success=False,
            error=result.get('error', 'Backup failed')
        )


@router.get("/list", summary="列出备份", description="获取备份列表")
async def list_backups(
        backup_type: Optional[str] = Query(None, pattern='^(database|files|full)$', description="备份类型过滤"),
        limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
        current_user=Depends(jwt_required),
):
    """列出备份"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    backups = backup_service.list_backups(
        backup_type=backup_type,
        limit=limit
    )

    return ApiResponse(
        success=True,
        data={
            'backups': backups,
            'count': len(backups),
        }
    )


@router.delete("/{backup_id}", summary="删除备份", description="删除指定的备份")
async def delete_backup(
        backup_id: str,
        current_user=Depends(jwt_required),
):
    """删除备份"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    success = backup_service.delete_backup(backup_id)

    if success:
        return ApiResponse(
            success=True,
            message="Backup deleted successfully"
        )
    else:
        return ApiResponse(
            success=False,
            error="Backup not found"
        )


@router.post("/cleanup", summary="清理旧备份", description="清理超过指定天数的旧备份")
async def cleanup_old_backups(
        days: int = Body(30, ge=1, le=365, description="保留天数"),
        backup_type: Optional[str] = Body(None, regex='^(database|files|full)$', description="备份类型过滤"),
        current_user=Depends(jwt_required),
):
    """清理旧备份"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = backup_service.cleanup_old_backups(
        days=days,
        backup_type=backup_type
    )

    return ApiResponse(
        success=True,
        message=f"Cleaned up {result['deleted']} old backups",
        data=result
    )


@router.get("/stats", summary="备份统计", description="获取备份统计信息")
async def get_backup_stats(
        current_user=Depends(jwt_required),
):
    """获取备份统计"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = backup_service.get_backup_stats()

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/schedule", summary="备份计划", description="获取自动备份计划配置")
async def get_backup_schedule(
        current_user=Depends(jwt_required),
):
    """获取备份计划"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # TODO: 从配置中读取实际的调度计划
    schedule = {
        'database': {
            'enabled': True,
            'frequency': 'daily',
            'time': '02:00',
            'retention_days': 30,
            'compress': True,
        },
        'files': {
            'enabled': True,
            'frequency': 'weekly',
            'day': 'sunday',
            'time': '03:00',
            'retention_days': 90,
            'compress': True,
        },
        'full': {
            'enabled': True,
            'frequency': 'monthly',
            'day': 1,
            'time': '04:00',
            'retention_days': 365,
            'compress': True,
        },
    }

    return ApiResponse(
        success=True,
        data=schedule
    )


@router.get("/examples", summary="使用示例", description="获取备份管理使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "backup_types": {
            'description': '备份类型说明',
            'types': {
                'database': {
                    'description': '仅备份数据库',
                    'use_case': '日常快速备份，恢复速度快',
                    'frequency': '建议每日备份',
                },
                'files': {
                    'description': '仅备份文件（媒体、主题、插件等）',
                    'use_case': '保护用户上传的内容和自定义文件',
                    'frequency': '建议每周备份',
                },
                'full': {
                    'description': '完整备份（数据库+文件）',
                    'use_case': '全面保护，可用于完整恢复',
                    'frequency': '建议每月备份',
                },
            }
        },
        "automation": {
            'description': '自动化备份',
            'example': '''
# 使用APScheduler设置定时任务
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.services.backup_service import backup_service

scheduler = AsyncIOScheduler()

# 每天凌晨2点备份数据库
scheduler.add_job(
    backup_service.create_database_backup,
    'cron',
    hour=2,
    minute=0,
    kwargs={'compress': True}
)

# 每周日凌晨3点备份文件
scheduler.add_job(
    backup_service.create_files_backup,
    'cron',
    day_of_week='sun',
    hour=3,
    minute=0,
    kwargs={'compress': True}
)

# 每月1号凌晨4点完整备份
scheduler.add_job(
    backup_service.create_full_backup,
    'cron',
    day=1,
    hour=4,
    minute=0,
    kwargs={'compress': True}
)

# 每天清理30天前的备份
scheduler.add_job(
    backup_service.cleanup_old_backups,
    'cron',
    hour=5,
    minute=0,
    kwargs={'days': 30}
)

scheduler.start()
            '''.strip()
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '实施3-2-1备份策略：3份副本，2种介质，1个异地',
                '定期测试备份恢复流程',
                '监控备份任务执行情况',
                '设置备份失败告警',
                '加密敏感数据的备份',
                '记录备份日志便于审计',
                '根据数据重要性调整备份频率',
                '保留足够长的备份历史',
            ]
        },
        "recovery_tips": {
            'description': '恢复提示',
            'tips': [
                '恢复前先停止应用服务',
                '验证备份文件的完整性',
                '在测试环境先演练恢复流程',
                '记录恢复步骤和时间',
                '恢复后验证数据完整性',
                '更新恢复文档',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
