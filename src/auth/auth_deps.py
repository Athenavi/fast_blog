"""
认证依赖项定义（使用 fastapi_users，不依赖 fastapi_jwt_auth）
"""
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel


# 从 fastapi_users 获取当前用户的依赖项
from src.auth.fastapi_users_auth import fastapi_users

async def get_current_user(
    user: UserModel = Depends(fastapi_users.current_user(active=True)),
) -> UserModel:
    """
    核心依赖：获取当前已验证的活跃用户。
    由 fastapi_users 自动处理 JWT 验证和用户加载。
    """
    return user


async def get_current_user_or_redirect(
    request: Request,
    user: Optional[UserModel] = Depends(fastapi_users.current_user(active=True, optional=True)),
):
    """
    页面路由版本：获取当前用户，未认证时返回重定向响应。
    """
    if user is None:
        # 任何认证失败都重定向到登录页
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}")
    return user


# ---------- 管理员权限依赖 ----------
async def admin_required(
    user: UserModel = Depends(get_current_user)
) -> UserModel:
    """API 路由：要求管理员权限"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return user


async def admin_required_page(
    request: Request,
    user_or_redirect = Depends(get_current_user_or_redirect),
):
    """页面路由：要求管理员权限，否则重定向登录页"""
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    if not user_or_redirect.is_superuser:
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}")
    return user_or_redirect


# ---------- 权限/角色依赖（API + Page 版本） ----------
def require_permission(permission_code: str):
    """检查特定权限（API 版本）"""
    async def checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if not user.has_permission(permission_code):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def require_role(role_name: str):
    """检查特定角色（API 版本）"""
    async def checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if not user.has_role(role_name):
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return user
    return checker


def require_permission_page(permission_code: str):
    """检查特定权限（页面版本，未认证重定向）"""
    async def checker(
        request: Request,
        user_or_redirect = Depends(get_current_user_or_redirect),
    ):
        if isinstance(user_or_redirect, RedirectResponse):
            return user_or_redirect
        if not user_or_redirect.has_permission(permission_code):
            return RedirectResponse(url=f"/login?next={request.url}")
        return user_or_redirect
    return checker


def require_role_page(role_name: str):
    """检查特定角色（页面版本，未认证重定向）"""
    async def checker(
        request: Request,
        user_or_redirect = Depends(get_current_user_or_redirect),
    ):
        if isinstance(user_or_redirect, RedirectResponse):
            return user_or_redirect
        if not user_or_redirect.has_role(role_name):
            return RedirectResponse(url=f"/login?next={request.url}")
        return user_or_redirect
    return checker


# ---------- JWT 直接认证依赖 ----------
async def jwt_required(user: UserModel = Depends(get_current_user)) -> UserModel:
    """别名：要求 JWT 认证（API 版本）"""
    return user


async def jwt_required_page(
    user_or_redirect = Depends(get_current_user_or_redirect),
):
    """页面版本：要求 JWT 认证，否则重定向"""
    return user_or_redirect


async def jwt_optional(
    user: Optional[UserModel] = Depends(fastapi_users.current_user(active=True, optional=True)),
) -> Optional[UserModel]:
    """可选的 JWT 认证，如果未提供有效 token 则返回 None"""
    return user


# ---------- VIP 依赖 ----------
def require_vip():
    """要求 VIP 成员资格"""
    async def checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if not user.is_vip():
            raise HTTPException(status_code=403, detail="VIP membership required")
        return user
    return checker


# ---------- 导出别名（兼容旧代码） ----------
# API 版本
jwt_required_dependency = jwt_required
jwt_optional_dependency = jwt_optional
admin_required_api = admin_required

# 页面版本
jwt_required_page_dependency = jwt_required_page
_get_current_active_user = get_current_user_or_redirect
async def authenticate_user_with_session(
    identifier: str,
    password: str,
    db: AsyncSession,
) -> Optional[UserModel]:
    """
    使用传入的数据库会话验证用户凭证。
    完全使用 SQLAlchemy，不依赖 Django。
    """
    import re
    from src.api.v1.user_utils import verify_password

    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    user = None

    if email_pattern.match(identifier):
        result = await db.execute(
            select(UserModel).where(UserModel.email == identifier)
        )
        user = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(UserModel).where(UserModel.username == identifier)
        )
        user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password):
        return None

    return user