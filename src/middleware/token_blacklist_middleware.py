"""
Token 黑名单中间件
检查每个请求的 JWT token 是否已被列入黑名单（用户登出、密码重置等）
使用内存缓存减少数据库查询
"""

import time
from collections import OrderedDict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.unified_logger import default_logger as logger


class TokenBlacklistMiddleware(BaseHTTPMiddleware):
    """Token 黑名单检查中间件（带内存缓存）"""

    #: 豁免路径：这些是**公开端点**，不检查黑名单。
    #:
    #: ⚠️ 下面列的全是 v2 路径，而 v2 已下线 —— 该清单当前不匹配任何请求，等效于
    #: "所有请求都检查黑名单"，属于**安全的一侧**。清理它时注意方向：把某个路径
    #: 加进来是**放宽**检查，只有在确认该端点确实无需鉴权时才可为之。
    EXEMPT_PATHS = [
        "/api/v2/auth/login",
        "/api/v2/auth/register",
        "/api/v2/auth/qr/generate",
        "/api/v2/articles/preview/",
        "/api/v2/articles/home/",
        "/api/v2/articles/p/",
    ]

    # 进程级 LRU 缓存：token_hash -> expiry_timestamp
    _cache = OrderedDict()
    _CACHE_MAX = 10000
    _CACHE_TTL = 300  # 5 分钟

    def _get_cached(self, token_hash: str) -> bool:
        """检查缓存中是否标记为黑名单，处理过期条目"""
        if token_hash in self._cache:
            expiry = self._cache[token_hash]
            if time.time() < expiry:
                return True  # 缓存命中：在黑名单中
            # 过期淘汰
            del self._cache[token_hash]
        return False

    def _set_cached(self, token_hash: str):
        """将 token 标记为黑名单（写入缓存）"""
        self._cache[token_hash] = time.time() + self._CACHE_TTL
        # LRU 淘汰
        if len(self._cache) > self._CACHE_MAX:
            self._cache.popitem(last=False)

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
                import hashlib
                token_hash = hashlib.sha256(token.encode()).hexdigest()

                # 1. 先查内存缓存
                if self._get_cached(token_hash):
                    logger.warning(f"Blacklisted token used (cache): {token[:16]}...")
                    raise HTTPException(status_code=401, detail="Token has been revoked")

                # 2. 再查数据库
                try:
                    from src.utils.database.unified_manager import db_manager
                    from shared.models.security import TokenBlacklist
                    from sqlalchemy import select

                    async with db_manager.get_session() as db:
                        result = await db.execute(
                            select(TokenBlacklist).where(
                                TokenBlacklist.token_hash == token_hash
                            )
                        )
                        blacklisted = result.scalar_one_or_none()

                        if blacklisted:
                            # 回填缓存
                            self._set_cached(token_hash)
                            logger.warning(f"Blacklisted token used (db): {token[:16]}...")
                            raise HTTPException(status_code=401, detail="Token has been revoked")
                except HTTPException:
                    raise
                except Exception as e:
                    # fail-closed：检查异常时拒绝请求比放行更安全
                    logger.error(f"Token blacklist check error, rejecting request: {e}")
                    raise HTTPException(status_code=401, detail="Token verification unavailable")

        return await call_next(request)
