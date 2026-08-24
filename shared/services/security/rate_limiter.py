"""
API限流服务
提供请求频率限制、IP限流、用户配额等功能
"""
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple

import redis.asyncio as redis
from fastapi import Request

from shared.logging import default_logger as logger


class RateLimiter:
    """
    API限流器

    功能:
    1. 基于Token Bucket算法的限流
    2. IP地址限流
    3. 用户级别限流
    4. API端点级别限流
    5. 配额管理
    """

    def __init__(self, redis_url: str = None):
        """
        初始化限流器

        Args:
            redis_url: Redis连接URL，如果为None则使用内存存储
        """
        self.redis_url = redis_url
        self.redis_client = None
        self._redis_attempted = False
        self.memory_store: Dict[str, list] = defaultdict(list)

        # 默认限流配置
        self.default_limits = {
            'global': {'requests': 1000, 'window': 3600},  # 全局：1000次/小时
            'ip': {'requests': 300, 'window': 60},  # IP：300次/分钟（约5次/秒，为媒体库页面多请求场景预留）
            'user': {'requests': 500, 'window': 3600},  # 用户：500次/小时
            'endpoint': {  # 端点特定限制
                '/api/v1/auth/login': {'requests': 10, 'window': 60},  # 登录：10次/分钟
                '/api/v1/articles': {'requests': 200, 'window': 3600},  # 文章：200次/小时
            }
        }

    async def initialize(self):
        """初始化Redis连接"""
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
                await self.redis_client.ping()
                logger.info("Redis rate limiter initialized")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, using memory store: {e}")
                self.redis_client = None

    async def ensure_redis(self):
        """惰性连接 Redis（生产环境优先使用 Redis，避免跨实例/多 worker 限流失效）"""
        if self.redis_client is not None or self._redis_attempted:
            return
        self._redis_attempted = True
        try:
            from src.setting import settings
            host = getattr(settings, 'REDIS_HOST', 'localhost') or 'localhost'
            port = int(getattr(settings, 'REDIS_PORT', 6379) or 6379)
            db = int(getattr(settings, 'REDIS_DB', 0) or 0)
            password = getattr(settings, 'REDIS_PASSWORD', None)
            url = (f"redis://:{password}@{host}:{port}/{db}" if password
                   else f"redis://{host}:{port}/{db}")
            self.redis_url = url
            await self.initialize()
        except Exception as e:
            logger.warning(f"Rate limiter Redis init failed, using memory store: {e}")
            self.redis_client = None

    def _get_key(self, prefix: str, identifier: str) -> str:
        """生成限流键"""
        return f"rate_limit:{prefix}:{identifier}"

    async def _add_request_memory(self, key: str, timestamp: float):
        """在内存中添加请求记录（限制单键长度，防止无界增长）"""
        lst = self.memory_store[key]
        lst.append(timestamp)
        if len(lst) > 2000:
            self.memory_store[key] = lst[-2000:]

    async def _get_request_count_memory(self, key: str, window: int) -> int:
        """从内存中获取窗口内的请求数"""
        now = time.time()
        cutoff = now - window

        # 清理过期记录
        self.memory_store[key] = [t for t in self.memory_store[key] if t > cutoff]

        return len(self.memory_store[key])

    async def _add_request_redis(self, key: str, timestamp: float, window: int):
        """在Redis中添加请求记录"""
        pipe = self.redis_client.pipeline()
        pipe.zadd(key, {str(timestamp): timestamp})
        pipe.expire(key, window)
        await pipe.execute()

    async def _get_request_count_redis(self, key: str, window: int) -> int:
        """从Redis中获取窗口内的请求数"""
        now = time.time()
        cutoff = now - window

        # 移除过期记录并计数
        count = await self.redis_client.zremrangebyscore(key, 0, cutoff)
        count = await self.redis_client.zcard(key)

        return count

    async def check_rate_limit(
            self,
            user_id: int = None,
            ip_address: str = None,
            endpoint: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查速率限制（优化版：单次检查 + 避免重复计数）

        注意：每个检查（IP/用户）只调用一次 is_rate_limited，
        避免旧实现对同一维度检查两次导致计数翻倍。

        Returns:
            (是否允许, 限流信息)
        """
        limit_info = {}

        # 检查 IP 限流（单次）
        if ip_address:
            limited, ip_info = await self.is_rate_limited(ip_address, 'ip', endpoint)
            if limited:
                return False, {
                    'retry_after': ip_info['window'],
                    'limit': {
                        'ip': {
                            'limit': ip_info['max_requests'],
                            'remaining': 0,
                            'reset': time.time() + ip_info['window']
                        }
                    }
                }
            limit_info['ip'] = {
                'limit': ip_info['max_requests'],
                'remaining': ip_info.get('remaining', ip_info['max_requests']),
                'reset': time.time() + ip_info['window']
            }

        # 检查用户限流（单次）
        if user_id:
            limited, user_info = await self.is_rate_limited(str(user_id), 'user', endpoint)
            if limited:
                return False, {
                    'retry_after': user_info['window'],
                    'limit': {
                        'user': {
                            'limit': user_info['max_requests'],
                            'remaining': 0,
                            'reset': time.time() + user_info['window']
                        }
                    }
                }
            quota = await self.get_quota_info(user_id)
            limit_info['user'] = {
                'limit': quota['quota_limit'],
                'remaining': quota['remaining'],
                'reset': quota['reset_time'].timestamp()
            }

        return True, {'limit': limit_info}

    async def is_rate_limited(
            self,
            identifier: str,
            limit_type: str = 'ip',
            endpoint: str = None,
            custom_limit: Dict[str, int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查是否被限流

        Args:
            identifier: 标识符（IP地址或用户ID）
            limit_type: 限流类型 ('ip', 'user', 'endpoint')
            endpoint: API端点路径
            custom_limit: 自定义限流配置

        Returns:
            (是否被限流, 限流信息)
        """
        # 获取限流配置
        if custom_limit:
            config = custom_limit
        elif endpoint and endpoint in self.default_limits['endpoint']:
            config = self.default_limits['endpoint'][endpoint]
        else:
            config = self.default_limits.get(limit_type, self.default_limits['global'])

        max_requests = config['requests']
        window = config['window']

        # 生成键
        key = self._get_key(limit_type, identifier)

        # 获取当前请求数
        now = time.time()

        if self.redis_client:
            request_count = await self._get_request_count_redis(key, window)
            await self._add_request_redis(key, now, window)
        else:
            request_count = await self._get_request_count_memory(key, window)
            await self._add_request_memory(key, now)

        # 检查是否超限
        if request_count >= max_requests:
            return True, {
                'limited': True,
                'current_count': request_count,
                'max_requests': max_requests,
                'window': window,
                'retry_after': window
            }

        return False, {
            'limited': False,
            'current_count': request_count + 1,
            'max_requests': max_requests,
            'window': window,
            'remaining': max_requests - (request_count + 1)
        }

    async def check_ip_limit(self, ip_address: str, endpoint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        检查IP限流

        Args:
            ip_address: IP地址
            endpoint: API端点

        Returns:
            (是否被限流, 限流信息)
        """
        return await self.is_rate_limited(ip_address, 'ip', endpoint)

    async def check_user_limit(self, user_id: int, endpoint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        检查用户限流

        Args:
            user_id: 用户ID
            endpoint: API端点

        Returns:
            (是否被限流, 限流信息)
        """
        return await self.is_rate_limited(str(user_id), 'user', endpoint)

    async def get_quota_info(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户配额信息

        Args:
            user_id: 用户ID

        Returns:
            配额信息
        """
        key = self._get_key('user', str(user_id))
        window = self.default_limits['user']['window']

        if self.redis_client:
            current_count = await self._get_request_count_redis(key, window)
        else:
            current_count = await self._get_request_count_memory(key, window)

        max_requests = self.default_limits['user']['requests']

        return {
            'user_id': user_id,
            'current_usage': current_count,
            'quota_limit': max_requests,
            'remaining': max(max_requests - current_count, 0),
            'window': window,
            'reset_time': datetime.now(timezone.utc) + timedelta(seconds=window)
        }

    async def set_custom_limit(self, identifier: str, limit_type: str, requests: int, window: int):
        """
        设置自定义限流配置

        Args:
            identifier: 标识符
            limit_type: 限流类型
            requests: 最大请求数
            window: 时间窗口（秒）
        """
        key = f"rate_limit_config:{limit_type}:{identifier}"

        config = {
            'requests': requests,
            'window': window
        }

        if self.redis_client:
            await self.redis_client.setex(key, 86400, str(config))  # 24小时过期
        else:
            # 内存存储
            self.memory_store[key] = [config]

    async def reset_limit(self, identifier: str, limit_type: str):
        """
        重置限流计数器

        Args:
            identifier: 标识符
            limit_type: 限流类型
        """
        key = self._get_key(limit_type, identifier)

        if self.redis_client:
            await self.redis_client.delete(key)
        else:
            if key in self.memory_store:
                del self.memory_store[key]


# 全局实例
rate_limiter = RateLimiter()


def _resolve_client_ip(request: Request) -> str:
    """解析客户端真实 IP（优先信任反向代理设置的 X-Forwarded-For / X-Real-IP）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first and first.lower() not in ("unknown", ""):
            return first
    real = request.headers.get("X-Real-IP")
    if real and real.strip():
        return real.strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """
    限流中间件

    自动对所有API请求进行限流检查
    """
    from fastapi.responses import JSONResponse

    # 使用真实客户端 IP（反向代理场景下避免全站共享一个 IP 桶）
    client_ip = _resolve_client_ip(request)

    # 生产环境优先使用 Redis 存储（多 worker/多实例共享限流计数）
    await rate_limiter.ensure_redis()

    # 获取API端点
    endpoint = request.url.path

    # 检查IP限流
    limited, info = await rate_limiter.check_ip_limit(client_ip, endpoint)

    if limited:
        return JSONResponse(
            status_code=429,
            content={
                'error': 'Rate limit exceeded',
                'retry_after': info['retry_after'],
                'message': f'Too many requests. Please try again in {info["retry_after"]} seconds.'
            },
            headers={
                'Retry-After': str(info['retry_after']),
                'X-RateLimit-Limit': str(info['max_requests']),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(time.time()) + info['retry_after'])
            }
        )

    # 继续处理请求
    response = await call_next(request)

    # 添加限流响应头
    response.headers['X-RateLimit-Limit'] = str(info['max_requests'])
    response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', info['max_requests']))
    response.headers['X-RateLimit-Reset'] = str(int(time.time()) + info['window'])

    return response
