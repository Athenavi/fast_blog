"""
CSRF Token API（已废弃）

FastBlog 使用 JWT Bearer 认证，前后端分离模式下 JWT 已天然防 CSRF。
该端点保留仅用于向后兼容，新代码不应依赖此功能。

替代方案：无需任何 CSRF 处理。JWT Access Token 通过 Authorization 头
或 HttpOnly Cookie 传输，攻击者无法跨站伪造认证请求。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter(tags=["csrf"])
logger = logging.getLogger(__name__)


_DEPRECATED_MSG = "CSRF token API is deprecated. JWT Bearer authentication inherently protects against CSRF in SPA deployments."


async def get_csrf_token(request: Request, current_user=Depends(jwt_required)):
    """获取 CSRF token（已废弃 — JWT 已天然防 CSRF）"""
    logger.warning(f"Deprecated CSRF token endpoint called by user {current_user.id}")
    import secrets
    from src.extensions import cache

    token = secrets.token_urlsafe(32)
    # Store in cache for 2 hours
    cache.set(f"csrf_token:{token}", str(current_user.id), ex=7200)

    return ok(data={
        "csrf_token": token,
        "expires_in": 7200,
        "_deprecated": True,
        "_message": _DEPRECATED_MSG,
    })
