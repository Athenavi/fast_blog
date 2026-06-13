"""
Token 黑名单中间件
检查每个请求的 JWT token 是否已被列入黑名单（用户登出、密码重置等）
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.unified_logger import default_logger as logger


class TokenBlacklistMiddleware(BaseHTTPMiddleware):
    """Token 黑名单检查中间件"""

    EXEMPT_PATHS = [
        "/api/v2/auth/login",
        "/api/v2/auth/register",
        "/api/v2/auth/qr/generate",
        "/api/v2/preview/",
        "/api/v2/articles/home/",
        "/api/v2/articles/p/",
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 跳过豁免路径
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        # 检查 Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token:
                try:
                    from src.utils.database.unified_manager import db_manager
                    from shared.models.security import TokenBlacklist
                    import hashlib
                    from sqlalchemy import select

                    token_hash = hashlib.sha256(token.encode()).hexdigest()

                    async with db_manager.get_session() as db:
                        result = await db.execute(
                            select(TokenBlacklist).where(
                                TokenBlacklist.token_hash == token_hash
                            )
                        )
                        blacklisted = result.scalar_one_or_none()

                        if blacklisted:
                            logger.warning(f"Blacklisted token used: {token[:16]}...")
                            raise HTTPException(status_code=401, detail="Token has been revoked")
                except HTTPException:
                    raise
                except Exception as e:
                    # If blacklist check fails, still allow the request
                    # but log the error (fail-open is safer here than blocking all traffic)
                    if not isinstance(e, HTTPException):
                        logger.error(f"Token blacklist check error: {e}")

        return await call_next(request)
