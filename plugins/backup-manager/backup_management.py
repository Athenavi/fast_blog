"""
数据备份和恢复API端点
提供完整的备份、恢复和管理功能
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.backup_manager import (
    create_full_backup,
    get_backup_list,
    restore_from_backup,
    delete_backup,
    get_database_stats
)
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/backup", tags=["backup"])


@router.post("/create")
async def create_backup(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建完整数据库备份
    
    注意：此操作需要管理员权限
    """
    try:
        # 添加管理员权限检查
        if not current_user.is_superuser:
            return ApiResponse(success=False, error="权限不足，仅管理员可执行备份")

        result = await create_full_backup(db=db)

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "创建备份失败")
            )

        return ApiResponse(
            success=True,
            data={
                "message": "备份创建成功",
                **result
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/list")
async def list_backups(
        current_user=Depends(jwt_required)
):
    """
    获取所有备份文件列表
    """
    try:
        backups = await get_backup_list()

        return ApiResponse(
            success=True,
            data={"backups": backups}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/restore")
async def restore_backup(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从备份文件恢复数据
    
    Body参数:
        backup_file: 备份文件名（必填）
        restore_options: 恢复选项（可选），包含：
            - articles: 是否恢复文章
            - categories: 是否恢复分类
            - pages: 是否恢复页面
            - menus: 是否恢复菜单
    """
    try:
        # 添加管理员权限检查
        if not current_user.is_superuser:
            return ApiResponse(success=False, error="权限不足，仅管理员可执行恢复")

        body = await request.json()
        backup_file = body.get("backup_file")
        restore_options = body.get("restore_options", None)

        if not backup_file:
            return ApiResponse(
                success=False,
                error="请指定要恢复的备份文件"
            )

        result = await restore_from_backup(
            db=db,
            backup_filename=backup_file,
            restore_options=restore_options
        )

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "恢复备份失败")
            )

        return ApiResponse(
            success=True,
            data={
                "message": "数据恢复成功",
                **result
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/{backup_filename}")
async def delete_backup_file(
        backup_filename: str,
        current_user=Depends(jwt_required)
):
    """
    删除备份文件
    
    Args:
        backup_filename: 备份文件名
    """
    try:
        # 添加管理员权限检查
        if not current_user.is_superuser:
            return ApiResponse(success=False, error="权限不足，仅管理员可删除备份")

        success = await delete_backup(backup_filename=backup_filename)

        if not success:
            return ApiResponse(
                success=False,
                error="删除备份失败，文件可能不存在"
            )

        return ApiResponse(
            success=True,
            data={"message": "备份文件已删除"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/stats")
async def get_db_stats(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取数据库统计信息
    """
    try:
        stats = await get_database_stats(db=db)

        return ApiResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/export")
async def export_data(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    导出数据为JSON格式（不保存为文件，直接返回）
    
    Body参数:
        export_type: 导出类型（full/articles/categories/pages/menus）
    """
    try:
        from shared.services.backup_manager import create_full_backup

        # 创建临时备份
        result = await create_full_backup(db=db)

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "导出数据失败")
            )

        # 读取备份文件内容
        from pathlib import Path
        backup_path = Path(result["backup_path"])

        with open(backup_path, 'r', encoding='utf-8') as f:
            import json
            backup_content = json.load(f)

        # 删除临时文件
        backup_path.unlink()

        return ApiResponse(
            success=True,
            data={
                "message": "数据导出成功",
                "content": backup_content
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
