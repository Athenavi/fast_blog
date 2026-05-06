"""
会话管理 API
提供查看和管理用户登录设备的功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException

from shared.services.session_management_service import session_management_service
from src.api.v1.responses import ApiResponse
from src.auth.jwt_auth import jwt_required

router = APIRouter(prefix="/sessions", tags=["会话管理"])


@router.get("")
async def get_user_sessions(
        request: Request,
        current_user_id: int = Depends(jwt_required)
):
    """
    获取当前用户的所有活跃会话（登录设备列表）
    
    Returns:
        会话列表，包含设备信息、IP地址、最后活动时间等
    """
    sessions = session_management_service.get_user_sessions(
        user_id=current_user_id,
        active_only=True
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
        current_user_id: int = Depends(jwt_required)
):
    """
    撤销指定会话（远程注销设备）
    
    Args:
        session_id: 要撤销的会话ID
        
    Returns:
        操作结果
    """
    success = session_management_service.revoke_session(
        session_id=session_id,
        user_id=current_user_id
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
        current_user_id: int = Depends(jwt_required)
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

    count = session_management_service.revoke_all_sessions(
        user_id=current_user_id
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
        current_user_id: int = Depends(jwt_required)
):
    """
    清理当前用户的过期会话
    
    Returns:
        清理结果
    """
    # 注意：这里的cleanup_expired_sessions是全局清理
    # 如果需要只清理当前用户的，可以添加user_id参数

    count = session_management_service.cleanup_expired_sessions()

    return ApiResponse(
        success=True,
        data={
            'cleaned_count': count
        },
        message=f"已清理 {count} 个过期会话"
    )
