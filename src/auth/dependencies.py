from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status, Request
from fastapi_users.exceptions import UserNotExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.security.jwt_handler import validate_token_from_request

if TYPE_CHECKING:
    from src.auth.user_manager import UserManager


# Note: We don't use OAuth2PasswordBearer since we're handling JWT tokens via cookies
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/jwt/login")


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """获取用户数据库实例"""
    yield SQLAlchemyUserDatabase(session, UserModel)


async def get_user_manager(user_db=Depends(get_user_db)):
    """获取用户管理器实例"""
    from src.auth.user_manager import UserManager
    yield UserManager(user_db)


# 修正获取当前活跃用户的方法
async def get_current_active_user(
        request: Request,
        user_manager: UserManager = Depends(get_user_manager)
):
    """获取当前活跃用户，优先从cookie获取token"""
    try:
        user = await validate_token_from_request(request, user_manager)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user or invalid token"
            )
        return user
    except UserNotExists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    except Exception as e:
        # 添加更详细的错误日志，便于调试
        print(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


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
