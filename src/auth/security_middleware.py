"""
安全中间件

提供 XSS 过滤、CSRF 保护、速率限制等安全功能
"""

import re
import time
from collections import defaultdict
from typing import Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class XSSFilterMiddleware(BaseHTTPMiddleware):
    """
    XSS 过滤中间件
    
    检查请求体中的内容，防止 XSS 攻击
    """

    # 危险的 HTML 模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]

    async def dispatch(self, request: Request, call_next):
        # 只检查 POST/PUT/PATCH 请求
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '')

            # 只检查 JSON 请求
            if 'application/json' in content_type:
                try:
                    body = await request.json()

                    # 递归检查所有字符串字段
                    if self._check_for_xss(body):
                        return JSONResponse(
                            status_code=400,
                            content={
                                "success": False,
                                "error": "Request contains potentially dangerous content (XSS detected)"
                            }
                        )
                except Exception:
                    # 如果解析失败，继续处理
                    pass

        response = await call_next(request)
        return response

    def _check_for_xss(self, data) -> bool:
        """递归检查数据中是否包含 XSS"""
        if isinstance(data, str):
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE | re.DOTALL):
                    return True
        elif isinstance(data, dict):
            for value in data.values():
                if self._check_for_xss(value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._check_for_xss(item):
                    return True

        return False


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF 保护中间件
    
    验证 CSRF token，防止跨站请求伪造
    """

    # 不需要 CSRF 验证的方法
    SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}

    # 排除的路径（如 API 端点使用 JWT 认证）
    EXCLUDED_PATHS = ['/api/', '/auth/', '/health']

    async def dispatch(self, request: Request, call_next):
        # GET/HEAD/OPTIONS 请求不需要 CSRF 验证
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # 检查是否在排除列表中
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)

        # 验证 CSRF token
        csrf_token = request.headers.get('X-CSRF-Token') or request.headers.get('X-XSRF-TOKEN')

        if not csrf_token:
            # 对于 API 请求，如果没有 CSRF token 但有 Authorization header，跳过检查
            auth_header = request.headers.get('Authorization')
            if auth_header:
                return await call_next(request)

            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "CSRF token missing"
                }
            )

        # 实现实际的 CSRF token 验证逻辑
        from src.extensions import cache

        stored_token = await cache.get(f"csrf_token:{csrf_token}")
        if not stored_token:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "CSRF token invalid or expired"
                }
            )
        
        # 验证后删除token(一次性使用)
        await cache.delete(f"csrf_token:{csrf_token}")

        response = await call_next(request)
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件
    
    限制单个 IP 的请求频率，防止滥用和 DDoS 攻击
    """

    # 不需要速率限制的路径
    EXCLUDED_PATHS = [
        '/api/v1/thumbnail',  # 缩略图接口（频繁访问，需要豁免）
        '/api/v1/media/',     # 媒体文件接口（图片加载需要豁免）
    ]

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        """
        初始化速率限制器
        
        Args:
            app: FastAPI 应用
            max_requests: 时间窗口内的最大请求数
            window_seconds: 时间窗口（秒）
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # 存储每个 IP 的请求记录 {ip: [timestamp1, timestamp2, ...]}
        self.request_log: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 检查是否在排除列表中（缩略图等频繁访问的接口）
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)

        # 检查速率限制
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Too many requests. Please try again later.",
                    "retry_after": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                }
            )

        response = await call_next(request)

        # 添加速率限制头
        remaining = self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 检查代理头
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, client_ip: str) -> bool:
        """检查是否超过速率限制"""
        now = time.time()
        window_start = now - self.window_seconds

        # 清理过期的请求记录
        self.request_log[client_ip] = [
            ts for ts in self.request_log[client_ip]
            if ts > window_start
        ]

        # 检查是否超过限制
        if len(self.request_log[client_ip]) >= self.max_requests:
            return False

        # 记录当前请求
        self.request_log[client_ip].append(now)
        return True

    def _get_remaining_requests(self, client_ip: str) -> int:
        """获取剩余请求数"""
        now = time.time()
        window_start = now - self.window_seconds

        current_requests = len([
            ts for ts in self.request_log[client_ip]
            if ts > window_start
        ])

        return max(0, self.max_requests - current_requests)


class SQLInjectionFilterMiddleware(BaseHTTPMiddleware):
    """
    SQL 注入过滤中间件
    
    检查请求参数中的 SQL 注入模式
    """

    # SQL 注入危险模式
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|#|/\*)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bAND\b\s+\d+\s*=\s*\d+)",
        r"(;\s*(DROP|DELETE|UPDATE))",
    ]

    async def dispatch(self, request: Request, call_next):
        # 检查查询参数
        query_params = dict(request.query_params)
        if self._check_sql_injection(query_params):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid request parameters (SQL injection detected)"
                }
            )

        # 检查 POST/PUT/PATCH 请求体
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '')

            if 'application/json' in content_type:
                try:
                    body = await request.json()
                    if self._check_sql_injection(body):
                        return JSONResponse(
                            status_code=400,
                            content={
                                "success": False,
                                "error": "Request body contains invalid content (SQL injection detected)"
                            }
                        )
                except Exception:
                    pass

        response = await call_next(request)
        return response

    def _check_sql_injection(self, data) -> bool:
        """递归检查 SQL 注入"""
        if isinstance(data, str):
            for pattern in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE):
                    return True
        elif isinstance(data, dict):
            for value in data.values():
                if self._check_sql_injection(value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._check_sql_injection(item):
                    return True

        return False


def create_security_middleware_stack(app, rate_limit_requests: int = 100, rate_limit_window: int = 60):
    """
    创建安全中间件栈
    
    Args:
        app: FastAPI 应用
        rate_limit_requests: 速率限制请求数
        rate_limit_window: 速率限制时间窗口（秒）
        
    Returns:
        添加了安全中间件的应用
    """
    # 按顺序添加中间件（后添加的先执行）

    # 1. SQL 注入过滤（最外层）
    app.add_middleware(SQLInjectionFilterMiddleware)

    # 2. XSS 过滤
    app.add_middleware(XSSFilterMiddleware)

    # 3. CSRF 保护
    app.add_middleware(CSRFProtectionMiddleware)

    # 4. 速率限制（最内层，最先执行）
    app.add_middleware(
        RateLimiterMiddleware,
        max_requests=rate_limit_requests,
        window_seconds=rate_limit_window
    )

    return app
