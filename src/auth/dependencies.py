"""
当前活跃用户获取（使用 PyJWT 替代 fastapi-jwt-auth）
"""
import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.setting import settings
from shared.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.token_blacklist import token_blacklist


async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """
    获取当前活跃用户（PyJWT 验证）
    支持从 Authorization header 或 cookie 自动提取 token
    """
    # 1. 提取 token
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
    else:
        # 兼容 cookie 方式，cookie 名称可依据你的配置调整
        token = request.cookies.get("access_token") or request.cookies.get("access_token_cookie")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 解码并验证 JWT
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,                # 你的签名密钥
            algorithms=[settings.JWT_ALGORITHM],    # 例如 "HS256"
            options={"verify_exp": True},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. 提取用户 ID（主题声明）
    user_id_str = payload.get("sub")
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

    # 4. 黑名单检查（如果启用）
    jti = payload.get("jti")
    if jti and token_blacklist.is_available and token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # 5. 从数据库加载用户
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