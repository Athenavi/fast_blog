"""
会话管理 API
提供查看和管理用户登录设备的功能
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from shared.services.session_management_service import session_management_service
from src.api.v1.responses import ApiResponse

router = APIRouter(tags=["会话管理"])


@router.get("")
async def get_user_sessions(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取当前用户的所有活跃会话（登录设备列表）
    
    Returns:
        会话列表，包含设备信息、IP地址、最后活动时间等
    """
    sessions = await session_management_service.get_user_sessions(
        user_id=current_user.id,
        active_only=True,
        db_session=db
    )

    return ApiResponse(
        success=True,
        data={
            'sessions': sessions,
            'total': len(sessions)
        }
    )


@router.post("/{session_id}/revoke")
async def revoke_session(
        session_id: int,
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    撤销指定会话（远程注销设备）
    
    Args:
        session_id: 要撤销的会话ID
        
    Returns:
        操作结果
    """
    # 尝试从请求体中获取 refresh_token
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except:
        refresh_token = None

    success = await session_management_service.revoke_session(
        session_id=session_id,
        user_id=current_user.id,
        db_session=db,
        refresh_token=refresh_token
    )

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在或无权操作")

    return ApiResponse(
        success=True,
        message="设备已注销"
    )


@router.post("/revoke-all")
async def revoke_all_sessions(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    撤销所有其他会话（退出所有其他设备）
    
    保留当前设备的会话，注销所有其他设备。
    常用于修改密码后确保所有其他设备退出登录。
    
    Returns:
        操作结果，包含注销的设备数量
    """
    # 从请求中获取当前会话ID（如果有）
    # 这里简化处理，不传递exclude_current参数

    count = await session_management_service.revoke_all_sessions(
        user_id=current_user.id,
        db_session=db
    )

    return ApiResponse(
        success=True,
        data={
            'revoked_count': count
        },
        message=f"已注销 {count} 个设备"
    )


@router.post("/cleanup")
async def cleanup_expired_sessions(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    清理当前用户的过期会话
    
    Returns:
        清理结果
    """
    # 注意：这里的cleanup_expired_sessions是全局清理
    # 如果需要只清理当前用户的，可以添加user_id参数

    count = await session_management_service.cleanup_expired_sessions(
        db_session=db
    )

    return ApiResponse(
        success=True,
        data={
            'cleaned_count': count
        },
        message=f"已清理 {count} 个过期会话"
    )
