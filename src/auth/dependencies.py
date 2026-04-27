from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status, Request
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import AccessToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.utils.database.main import get_async_session

if TYPE_CHECKING:
    pass


# Note: We don't use OAuth2PasswordBearer since we're handling JWT tokens via cookies
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/jwt/login")


async def get_current_active_user(
        request: Request,
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取当前活跃用户，使用 Django simplejwt 验证 token
    优先从 cookie 获取 token，其次从 Authorization header 获取
    """
    try:
        # 首先尝试从 cookie 获取 token
        access_token = request.cookies.get("access_token")

        if not access_token:
            # 如果 cookie 中没有 token，尝试从 Authorization header 获取
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                access_token = authorization[7:]

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 使用 Django simplejwt 验证 token
        try:
            valid_token = AccessToken(access_token)
            user_id = valid_token['user_id']
        except (TokenError, InvalidToken) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # 从数据库获取用户
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_super_user(
        request: Request,
        user: UserModel = Depends(get_current_active_user)
) -> UserModel:
    """获取当前超级用户"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return user
