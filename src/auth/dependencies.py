"""
当前活跃用户获取（完全基于 fastapi-jwt-auth，替代 Django simplejwt）
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.token_blacklist import token_blacklist


async def get_current_active_user(
        request: Request,
        db: AsyncSession = Depends(get_async_session),
        Authorize: AuthJWT = Depends(),
) -> UserModel:
    """
    获取当前活跃用户（fastapi-jwt-auth 验证）
    支持从 cookie 或 Authorization header 自动提取 token
    """
    # 1. 验证 JWT（fastapi-jwt-auth 会自动从 cookie/header 获取 token）
    try:
        Authorize.jwt_required()
    except AuthJWTException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 提取用户 ID（主题声明）
    user_id_str = Authorize.get_jwt_subject()
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )

    # 3. 黑名单检查（如果启用）
    raw_jwt = Authorize.get_raw_jwt()
    if raw_jwt and token_blacklist.is_available:
        jti = raw_jwt.get("jti")
        if jti and token_blacklist.is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    # 4. 从数据库加载用户
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


async def get_current_super_user(
        user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """要求当前用户为超级管理员"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return user
