"""V3 鉴权工具：JWT 签发/解析 + token 黑名单 + 密码校验

token 负载与 v2（``src/api/v2/auth_legacy/__init__.py:76``）**保持一致**，这样 v2 与 v3 签发的
token 都能被同一套鉴权依赖（``src/auth/auth_deps.py``）接受：:

    {"sub": "<user_id>", "iat": ..., "exp": ..., "jti": ..., "type": "access" | "refresh"}

迁移说明：这些工具本应属于 ``src/auth/``。当前 v2 的实现仍在 ``auth_legacy`` 内，为避免
两处实现漂移，v3 在此提供等价实现；待 v2 下线时把本模块提升到 ``src/auth/``。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Request
from jwt.exceptions import InvalidTokenError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.models.user import User as UserModel
from src.api.v3.core.exceptions import UnauthorizedError
from src.api.v3.core.logger import get_logger

logger = get_logger("security")

_blacklist_instance = None


def get_token_blacklist():
    """惰性获取 token 黑名单（Redis 不可用时自动降级为不可用）"""
    global _blacklist_instance
    if _blacklist_instance is None:
        from src.utils.token_blacklist import token_blacklist

        _blacklist_instance = token_blacklist
    return _blacklist_instance


def issue_token(
    subject: str,
    token_type: str = "access",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """签发 token（``token_type`` 为 access / refresh / temp_2fa）"""
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        seconds = (
            settings.JWT_EXPIRATION_DELTA
            if token_type == "access"
            else settings.REFRESH_TOKEN_EXPIRATION_DELTA
        )
        expires_delta = timedelta(seconds=seconds)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 token；失败或已被吊销时抛 ``UnauthorizedError``"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
    except InvalidTokenError as exc:
        raise UnauthorizedError("令牌无效或已过期") from exc

    jti = payload.get("jti")
    blacklist = get_token_blacklist()
    if jti and blacklist.is_available and blacklist.is_blacklisted(jti):
        raise UnauthorizedError("令牌已失效")
    return payload


def extract_token(request: Request) -> Optional[str]:
    """从请求取 access token：优先 Bearer，其次 cookie（与 v2 行为一致）"""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token") or request.cookies.get("access_token_cookie")


def revoke_token(token: str) -> bool:
    """把 token 加入黑名单（登出用）"""
    blacklist = get_token_blacklist()
    if not token or not blacklist.is_available:
        return False
    try:
        payload = decode_token(token)
        blacklist.blacklist(payload["jti"], payload["exp"])
        return True
    except Exception:  # noqa: BLE001 - 登出失败不应影响用户体验
        logger.exception("token 加入黑名单失败")
        return False


async def authenticate_user(
    db: AsyncSession,
    identifier: str,
    password: str,
) -> Optional[UserModel]:
    """按用户名或邮箱校验密码，成功返回用户，失败返回 None"""
    from src.utils.security.password_validator import verify_password

    user = await db.scalar(
        select(UserModel).where(
            or_(UserModel.username == identifier, UserModel.email == identifier)
        )
    )
    if not user or not user.password:
        return None
    return user if verify_password(password, user.password) else None


# ---------- cookie 策略（system/auth 与 mobile/auth 共用） ----------
ACCESS_COOKIE_MAX_AGE = 3600
REFRESH_COOKIE_MAX_AGE = 2592000


def is_https() -> bool:
    return str(getattr(settings, "SITE_URL", "")).startswith("https://")


def set_auth_cookies(response: Any, data: dict) -> None:
    """写入 access / refresh cookie（httponly + samesite=strict，HTTPS 下自动加 secure）"""
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    if access_token:
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=is_https(),
            samesite="strict",
            max_age=ACCESS_COOKIE_MAX_AGE,
            path="/",
        )
    if refresh_token:
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=True,
            secure=is_https(),
            samesite="strict",
            max_age=REFRESH_COOKIE_MAX_AGE,
            path="/",
        )


def clear_auth_cookies(response: Any) -> None:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
