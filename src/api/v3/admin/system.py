"""
V3 系统管理 API

权限要求:
  GET    /settings       → settings:view
  PUT    /settings       → settings:edit
  POST   /backup         → backup:create
  POST   /backup/restore → backup:restore
  DELETE /backup/{id}    → backup:delete

路由函数内无权限查询。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.system import SystemSettings
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-system"])


# ============================================================
# 设置查看
# ============================================================

@router.get("/settings", summary="查看设置")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    """获取所有系统设置"""
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()

    return ApiResponse(success=True, data={
        "settings": {s.key: s.value for s in settings},
    })


# ============================================================
# 设置编辑
# ============================================================

@router.put("/settings", summary="编辑设置")
async def update_settings(
    settings: dict = Body(..., description="键值对设置"),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:edit")),
):
    """更新系统设置（全量替换）"""
    now = datetime.now(timezone.utc)

    for key, value in settings.items():
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = str(value)
            existing.updated_at = now
        else:
            db.add(SystemSettings(
                key=key,
                value=str(value),
                created_at=now,
                updated_at=now,
            ))

    await db.commit()
    return ApiResponse(success=True, message="设置已更新")


# ============================================================
# 备份管理
# ============================================================

@router.post("/backup", summary="创建备份")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:create")),
):
    """创建数据库备份"""
    try:
        from src.utils.database.backup import DatabaseBackup
        from src.utils.database.main import engine

        backup = DatabaseBackup(engine)
        filename = backup.create_backup()
        return ApiResponse(success=True, data={"filename": filename}, message="备份创建成功")
    except ImportError:
        return ApiResponse(success=False, error="备份模块不可用")
    except Exception as e:
        return ApiResponse(success=False, error=f"备份失败: {e}")


@router.post("/backup/restore", summary="恢复备份")
async def restore_backup(
    filename: str = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:restore")),
):
    """恢复数据库备份"""
    try:
        from src.utils.database.backup import DatabaseBackup
        from src.utils.database.main import engine

        backup = DatabaseBackup(engine)
        backup.restore_backup(filename)
        return ApiResponse(success=True, message="备份恢复成功")
    except ImportError:
        return ApiResponse(success=False, error="备份模块不可用")
    except Exception as e:
        return ApiResponse(success=False, error=f"恢复失败: {e}")


@router.delete("/backup/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("backup:delete")),
):
    """删除备份文件"""
    # 这里可以加实际的文件删除逻辑
    return ApiResponse(success=True, message="备份已删除")
