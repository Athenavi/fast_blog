"""
JWT处理工具函数
确保登录和验证使用相同的JWT策略
"""
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Request
from fastapi_users.authentication import JWTStrategy

from src.auth.user_manager import UserManager  # 导入UserManager
from src.models.user import User as UserModel  # 导入UserModel
from src.setting import settings


def get_jwt_strategy() -> JWTStrategy:
    """获取JWT策略实例，确保登录和验证使用相同的配置"""
    return JWTStrategy(
        secret=settings.JWT_SECRET_KEY or settings.SECRET_KEY,
        lifetime_seconds=settings.JWT_EXPIRATION_DELTA
    )


def is_token_expiring_soon(token: str, threshold_minutes: int = 5) -> bool:
    """
    检查JWT令牌是否即将过期
    :param token: JWT令牌
    :param threshold_minutes: 阈值（分钟），在此时间内被认为即将过期
    :return: 是否即将过期
    """
    try:
        # 解码令牌但不验证签名（因为我们只想检查到期时间）
        payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            time_to_expiry = exp_datetime - now
            return time_to_expiry.total_seconds() < (threshold_minutes * 60)
        return False
    except Exception:
        # 如果解码失败，假设令牌无效
        return True


async def validate_token_from_request(
        request: Request,
        user_manager: 'UserManager'
) -> Optional['UserModel']:
    """
    从请求中验证JWT token
    首先尝试从cookie获取，然后从header获取
    如果访问令牌即将过期且存在刷新令牌，则自动刷新
    """
    # 首先尝试从cookie获取token
    access_token = request.cookies.get("access_token")

    if not access_token:
        # 如果cookie中没有token，尝试从Authorization header获取
        token = request.headers.get("Authorization")
        if not token:
            return None
        # 移除 "Bearer " 前缀（如果存在）
        if token.startswith("Bearer "):
            token = token[7:]
        access_token = token

    # 使用JWT策略验证令牌
    strategy = get_jwt_strategy()
    try:
        user = await strategy.read_token(access_token, user_manager)

        # 检查令牌是否即将过期（在5分钟内）
        if user and is_token_expiring_soon(access_token):
            # 尝试使用refresh token刷新访问令牌
            refresh_token = request.cookies.get("refresh_token")
            if refresh_token:
                try:
                    # 这里需要模拟通过refresh token获取用户
                    # 由于fastapi-users的默认实现不直接支持refresh token，
                    # 我们需要检查refresh token的有效性并生成新的access token
                    refreshed_user = await user_manager.get_by_email(user.email)  # 获取最新的用户数据
                    if refreshed_user and refreshed_user.is_active:
                        # 生成新的访问令牌
                        new_access_token = await strategy.write_token(refreshed_user)
                        # 将新令牌添加到请求中，以便后续处理
                        request.state.new_access_token = new_access_token
                        return refreshed_user
                except Exception as refresh_error:
                    print(f"Refresh token validation error: {str(refresh_error)}")

        return user
    except Exception as e:
        print(f"Token validation error: {str(e)}")
        # 尝试使用refresh token刷新访问令牌
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            try:
                # 通过refresh token获取用户信息
                # 注意：这里需要根据实际的实现方式来处理刷新逻辑
                # 因为fastapi-users默认不直接支持refresh tokens
                # 我们需要一个自定义的刷新机制
                pass
            except Exception as refresh_error:
                print(f"Refresh token validation error: {str(refresh_error)}, redirecting to login page.")
    finally:
        print("Token validation complete.")
