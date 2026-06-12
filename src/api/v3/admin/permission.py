"""
V3 权限校验 API

提供前端权限检查端点，供 PermissionGuard 组件调用。
"""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission
from shared.services.security.rbac_service import rbac_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-permission"])


@router.post("/check-permission", summary="检查当前用户权限")
async def check_permission(
    permission_code: str = Body(...),
    user_id: int = Body(0),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """检查当前用户是否有指定权限代码"""
    # user_id=0 表示检查当前用户
    uid = user_id if user_id > 0 else current_user.id

    has = await rbac_service.has_capability(db, uid, permission_code)
    return ApiResponse(success=True, data={
        "user_id": uid,
        "permission_code": permission_code,
        "has_permission": has,
    })
