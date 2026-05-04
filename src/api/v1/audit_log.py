"""
审计日志 API

提供活动日志的查询、搜索和导出功能
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.audit_log_service import AuditLogService
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session

router = APIRouter()


@router.get("", summary="获取审计日志列表", description="查询系统活动日志，支持多种过滤条件")
async def get_audit_logs(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        user_id: Optional[int] = Query(None, description="用户ID过滤"),
        activity_type: Optional[str] = Query(None, description="活动类型过滤"),
        target_type: Optional[str] = Query(None, description="目标类型过滤"),
        start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
        end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)"),
        search_keyword: Optional[str] = Query(None, description="搜索关键词"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session),
):
    """
    获取审计日志列表
    
    只有管理员可以查看所有日志，普通用户只能查看自己的日志
    """
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)

    # 如果不是管理员，只能查看自己的日志
    if not is_admin:
        user_id = current_user.id

    # 解析日期
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")

    # 创建服务实例
    service = AuditLogService(db)

    # 获取日志
    activities, total = await service.get_activities(
        page=page,
        per_page=per_page,
        user_id=user_id,
        activity_type=activity_type,
        target_type=target_type,
        start_date=start_dt,
        end_date=end_dt,
        search_keyword=search_keyword,
    )

    # 格式化数据
    formatted_activities = [service.format_activity_for_display(activity) for activity in activities]

    return ApiResponse(
        success=True,
        data=formatted_activities,
        pagination={
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            "has_next": page < (total + per_page - 1) // per_page if per_page > 0 else False,
            "has_prev": page > 1,
        }
    )


@router.get("/{activity_id}", summary="获取活动详情", description="获取单个活动的详细信息")
async def get_activity_detail(
        activity_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session),
):
    """获取单个活动的详细信息"""
    service = AuditLogService(db)

    activity = await service.get_activity_detail(activity_id)

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin and activity.user != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    return ApiResponse(
        success=True,
        data=service.format_activity_for_display(activity)
    )


@router.post("/cleanup", summary="清理旧日志", description="删除指定天数之前的活动日志")
async def cleanup_old_logs(
        days: int = Query(90, ge=1, le=365, description="保留天数"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session),
):
    """
    清理旧的活动日志
    
    只有超级管理员可以执行此操作
    """
    # 检查权限
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Only superadmin can perform this action")

    service = AuditLogService(db)
    deleted_count = await service.delete_old_activities(days=days)

    await db.commit()

    return ApiResponse(
        success=True,
        message=f"Successfully deleted {deleted_count} old activity records",
        data={"deleted_count": deleted_count}
    )


@router.get("/types/activities", summary="获取活动类型列表", description="获取所有可用的活动类型")
async def get_activity_types():
    """获取所有可用的活动类型"""
    service = AuditLogService.__new__(AuditLogService)
    return ApiResponse(
        success=True,
        data={
            "activity_types": service.ACTIVITY_TYPES,
            "target_types": service.TARGET_TYPES,
        }
    )
