"""
FastAPI Users 认证配置
独立的认证后端配置，避免循环导入
"""
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend, BearerTransport

from shared.models.user import User as UserModel
from src.auth.user_manager import get_user_manager
from src.setting import settings


def get_jwt_strategy() -> JWTStrategy:
    """获取 JWT 策略"""
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)


# 认证后端
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=BearerTransport(tokenUrl="auth/jwt/login"),
    get_strategy=get_jwt_strategy,
)

# FastAPI Users 实例
fastapi_users = FastAPIUsers[UserModel, int](
    get_user_manager,
    [auth_backend],
)
