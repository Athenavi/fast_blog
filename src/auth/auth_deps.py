"""
认证依赖项定义（完全使用 fastapi-jwt-auth，不依赖 Django）
"""
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.token_blacklist import token_blacklist


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    Authorize: AuthJWT = Depends(),
) -> UserModel:
    """
    核心依赖：获取当前已验证的活跃用户。
    1. 验证 JWT token（从 cookie 或 header 获取）
    2. 检查 token 是否在黑名单中
    3. 从数据库加载用户，确保存在且激活
    """
    # 验证 JWT
    try:
        Authorize.jwt_required()
    except AuthJWTException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 提取用户 ID
    user_id_str = Authorize.get_jwt_subject()
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
        )
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )

    # 黑名单检查（如已启用）
    raw_jwt = Authorize.get_raw_jwt()
    if raw_jwt and token_blacklist.is_available:
        jti = raw_jwt.get("jti")
        if jti and token_blacklist.is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    # 从数据库加载用户
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )

    return user


async def get_current_user_or_redirect(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    Authorize: AuthJWT = Depends(),
):
    """
    页面路由版本：获取当前用户，未认证时返回重定向响应。
    """
    try:
        user = await get_current_user(request, db, Authorize)
        return user
    except HTTPException:
        # 任何认证失败都重定向到登录页
        next_url = str(request.url)
        return RedirectResponse(url=f"/login?next={next_url}")


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
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    Authorize: AuthJWT = Depends(),
) -> Optional[UserModel]:
    """可选的 JWT 认证，如果未提供有效 token 则返回 None"""
    try:
        return await get_current_user(request, db, Authorize)
    except HTTPException:
        return None


# ---------- VIP 依赖 ----------
def require_vip():
    """要求 VIP 成员资格"""
    async def checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if not user.is_vip():
            raise HTTPException(status_code=403, detail="VIP membership required")
        return user
    return checker


# ---------- 用户认证函数（保留，用于登录流程） ----------
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