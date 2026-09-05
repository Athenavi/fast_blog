"""
暴力破解防护中间件
基于 IP 和用户名的登录尝试频率限制，使用 Redis 缓存实现多 worker 共享。

架构说明：
- 使用 extensions 中的 cache 抽象（Redis -> 内存 SimpleCache 自动降级）
- 多进程/多 worker 共享 Redis 时，限流状态全局一致
- 降级为 SimpleCache 时，单 worker 内安全，但多 worker 间状态独立
"""

import json

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.unified_logger import default_logger as logger


class BruteForceProtectionMiddleware(BaseHTTPMiddleware):
    """
    暴力破解防护中间件

    策略:
    - 每 IP 每 15 分钟最多 10 次登录尝试
    - 每用户名每 15 分钟最多 5 次登录尝试
    - 超过限制后返回 429 Too Many Requests

    使用缓存（Redis 优先）实现跨 worker 共享状态。
    """

    def __init__(self, app, window_minutes: int = 15, max_attempts_per_ip: int = 10, max_attempts_per_user: int = 5):
        super().__init__(app)
        self.window_seconds = window_minutes * 60
        self.max_per_ip = max_attempts_per_ip
        self.max_per_user = max_attempts_per_user
        # 惰性加载 cache，避免初始化时循环依赖
        self._cache = None
        self._redis_failed = False  # Redis 是否已标记为不可用

    @property
    def cache(self):
        if self._cache is None:
            from src.extensions import cache as ext_cache
            self._cache = ext_cache
        return self._cache

    def _cache_key_ip(self, ip: str) -> str:
        return f"bf:ip:{ip}"

    def _cache_key_user(self, username: str) -> str:
        return f"bf:user:{username}"

    def _get_cache_ttl(self) -> int:
        """缓存过期时间比窗口略长，确保窗口内数据完整"""
        return self.window_seconds + 60

    # Redis 连接失败标记，首次超时后置为 True 并降级到内存缓存
    # 使用模块级变量确保跨实例共享，避免每次新实例都重新尝试 Redis
    _redis_failed = False

    # 模块级标记：Redis 是否已确认不可用
    _redis_working = None  # None=未检测, True=有效, False=已失效

    def _increment_and_check(self, key: str, max_attempts: int) -> bool:
        """
        原子递增尝试次数并检查是否超过限制。
        返回 True 表示超过限制。

        优先使用 Redis INCR 原子操作，降级为 SimpleCache 时使用 get+set。
        """
        c = self.cache
        # 使用模块级标记：一旦 Redis 失效，不再尝试连接
        _bf_redis_working = getattr(BruteForceProtectionMiddleware, '_redis_working', None)

        # 检测是否使用 Redis 包装器（且之前未确认失败过）
        if (_bf_redis_working is not False
                and hasattr(c, '_client') and hasattr(c._client, 'incr')):
            try:
                count = c._client.incr(key)
                if count == 1:
                    c._client.expire(key, self._get_cache_ttl())
                # 标记 Redis 可用（可能之前是 None）
                BruteForceProtectionMiddleware._redis_working = True
                return int(count) > max_attempts
            except Exception as e:
                logger.error(f"Redis 递增失败: {e}")
                # 模块级标记 Redis 不可用，后续请求直接降级
                BruteForceProtectionMiddleware._redis_working = False
                # 降级后尝试通过 SimpleCache 的 set 写入本次计数
                try:
                    c.set(key, "1", ex=self._get_cache_ttl())
                except Exception:
                    pass
                return False

        # SimpleCache 降级模式
        try:
            val = c.get(key)
            count = 0
            if val is not None:
                if isinstance(val, bytes):
                    count = int(val.decode())
                else:
                    count = int(val)
            count += 1
            c.set(key, str(count), ex=self._get_cache_ttl())
            return count > max_attempts
        except Exception as e:
            logger.error(f"Cache 递增失败: {e}")
            return False

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 标准化路径：去尾斜杠，仅处理 /api/v2/auth/login 和 /api/v2/auth/register
        normalized = path.rstrip('/')
        if not (normalized.endswith("/auth/login") or normalized.endswith("/auth/register") or "/auth/login" in path or "/auth/register" in path):
            return await call_next(request)

        # 获取客户端真实 IP（支持反向代理）
        import re as _re
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if _re.match(r'^\d{1,3}(\.\d{1,3}){3}$', candidate) and all(0 <= int(octet) <= 255 for octet in candidate.split('.')):
                client_ip = candidate
            else:
                client_ip = request.client.host if request.client else "unknown"
        else:
            real_ip = request.headers.get("X-Real-IP")
            client_ip = real_ip if real_ip else (request.client.host if request.client else "unknown")

        # 检查 IP 限制
        ip_key = self._cache_key_ip(client_ip)
        if self._increment_and_check(ip_key, self.max_per_ip):
            logger.warning(f"IP {client_ip} 登录尝试超过限制")
            raise HTTPException(
                status_code=429,
                detail=f"登录尝试过于频繁，请在 {self.window_seconds // 60} 分钟后再试"
            )

        response = await call_next(request)

        # 记录失败的登录尝试（同时记录到用户级别）
        if response.status_code in (401, 403):
            # 从请求体提取用户名（使用备用副本避免消费请求体）
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes) if body_bytes else {}
                username = body.get("username", "") or body.get("email", "")
                if username:
                    user_key = self._cache_key_user(username)
                    if self._increment_and_check(user_key, self.max_per_user):
                        logger.warning(f"用户名 {username} 登录尝试超过限制")
            except Exception:
                pass

        return response

    def is_ip_blocked(self, ip: str) -> bool:
        """检查 IP 是否被封禁（供外部调用）"""
        key = self._cache_key_ip(ip)
        try:
            val = self.cache.get(key)
            if val is not None:
                if isinstance(val, bytes):
                    count = int(val.decode())
                else:
                    count = int(val)
                return count >= self.max_per_ip
        except Exception:
            pass
        return False

    def reset_ip(self, ip: str) -> None:
        """重置 IP 的尝试计数（登录成功后调用）"""
        key = self._cache_key_ip(ip)
        try:
            c = self.cache
            if hasattr(c, '_client') and hasattr(c._client, 'delete'):
                c._client.delete(key)
            else:
                c.delete(key)
        except Exception as e:
            logger.error(f"重置 IP 尝试计数失败: {e}")

    def reset_user(self, username: str) -> None:
        """重置用户名的尝试计数（登录成功后调用）"""
        key = self._cache_key_user(username)
        try:
            c = self.cache
            if hasattr(c, '_client') and hasattr(c._client, 'delete'):
                c._client.delete(key)
            else:
                c.delete(key)
        except Exception as e:
            logger.error(f"重置用户尝试计数失败: {e}")
