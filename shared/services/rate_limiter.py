"""
API速率限制服务

实现令牌桶算法的速率限制
支持用户级和IP级限制
"""

import time
from typing import Dict, Optional, Tuple


class TokenBucket:
    """
    令牌桶实现
    
    用于控制请求速率
    """

    def __init__(self, rate: float, capacity: int):
        """
        初始化令牌桶
        
        Args:
            rate: 令牌生成速率（每秒）
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        消费令牌
        
        Args:
            tokens: 需要消费的令牌数
        
        Returns:
            是否成功消费
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill

        # 计算新增令牌数
        new_tokens = elapsed * self.rate

        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = now

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        获取等待时间
        
        Args:
            tokens: 需要的令牌数
        
        Returns:
            需要等待的秒数
        """
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.rate


class RateLimiter:
    """
    速率限制器
    
    支持多种限制策略
    """

    def __init__(self):
        """初始化速率限制器"""
        # 用户级限制 {user_id: TokenBucket}
        self.user_buckets: Dict[int, TokenBucket] = {}

        # IP级限制 {ip_address: TokenBucket}
        self.ip_buckets: Dict[str, TokenBucket] = {}

        # 全局限制
        self.global_bucket = TokenBucket(rate=100, capacity=1000)

        # 默认配置
        self.default_config = {
            'user_rate': 10,  # 用户每秒请求数
            'user_capacity': 100,  # 用户桶容量
            'ip_rate': 5,  # IP每秒请求数
            'ip_capacity': 50,  # IP桶容量
        }

        # 自定义配置 {endpoint: config}
        self.endpoint_configs: Dict[str, Dict[str, float]] = {}

    def configure_endpoint(
            self,
            endpoint: str,
            user_rate: Optional[float] = None,
            user_capacity: Optional[int] = None,
            ip_rate: Optional[float] = None,
            ip_capacity: Optional[int] = None
    ):
        """
        配置端点的速率限制
        
        Args:
            endpoint: API端点路径
            user_rate: 用户速率限制
            user_capacity: 用户容量
            ip_rate: IP速率限制
            ip_capacity: IP容量
        """
        config = {}

        if user_rate is not None:
            config['user_rate'] = user_rate
        if user_capacity is not None:
            config['user_capacity'] = user_capacity
        if ip_rate is not None:
            config['ip_rate'] = ip_rate
        if ip_capacity is not None:
            config['ip_capacity'] = ip_capacity

        self.endpoint_configs[endpoint] = config

    def check_rate_limit(
            self,
            user_id: Optional[int] = None,
            ip_address: Optional[str] = None,
            endpoint: Optional[str] = None,
            tokens: int = 1
    ) -> Tuple[bool, Dict[str, any]]:
        """
        检查速率限制
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            endpoint: API端点
            tokens: 需要的令牌数
        
        Returns:
            (是否允许, 限制信息)
        """
        # 获取端点配置
        config = self.endpoint_configs.get(endpoint, {})

        user_rate = config.get('user_rate', self.default_config['user_rate'])
        user_capacity = config.get('user_capacity', self.default_config['user_capacity'])
        ip_rate = config.get('ip_rate', self.default_config['ip_rate'])
        ip_capacity = config.get('ip_capacity', self.default_config['ip_capacity'])

        info = {
            'allowed': True,
            'limit': {},
            'retry_after': 0,
        }

        # 检查全局限制
        if not self.global_bucket.consume(tokens):
            wait_time = self.global_bucket.get_wait_time(tokens)
            info['allowed'] = False
            info['retry_after'] = wait_time
            info['limit']['global'] = {
                'limit': self.global_bucket.capacity,
                'remaining': max(0, int(self.global_bucket.tokens)),
                'reset': time.time() + wait_time,
            }
            return False, info

        # 检查用户限制
        if user_id:
            if user_id not in self.user_buckets:
                self.user_buckets[user_id] = TokenBucket(user_rate, user_capacity)

            bucket = self.user_buckets[user_id]

            if not bucket.consume(tokens):
                wait_time = bucket.get_wait_time(tokens)
                info['allowed'] = False
                info['retry_after'] = max(info['retry_after'], wait_time)
                info['limit']['user'] = {
                    'limit': bucket.capacity,
                    'remaining': max(0, int(bucket.tokens)),
                    'reset': time.time() + wait_time,
                }
                return False, info

            info['limit']['user'] = {
                'limit': bucket.capacity,
                'remaining': max(0, int(bucket.tokens)),
                'reset': time.time() + (bucket.capacity - bucket.tokens) / user_rate,
            }

        # 检查IP限制
        if ip_address:
            if ip_address not in self.ip_buckets:
                self.ip_buckets[ip_address] = TokenBucket(ip_rate, ip_capacity)

            bucket = self.ip_buckets[ip_address]

            if not bucket.consume(tokens):
                wait_time = bucket.get_wait_time(tokens)
                info['allowed'] = False
                info['retry_after'] = max(info['retry_after'], wait_time)
                info['limit']['ip'] = {
                    'limit': bucket.capacity,
                    'remaining': max(0, int(bucket.tokens)),
                    'reset': time.time() + wait_time,
                }
                return False, info

            info['limit']['ip'] = {
                'limit': bucket.capacity,
                'remaining': max(0, int(bucket.tokens)),
                'reset': time.time() + (bucket.capacity - bucket.tokens) / ip_rate,
            }

        return True, info

    def get_user_usage(self, user_id: int) -> Dict[str, any]:
        """
        获取用户使用情况
        
        Args:
            user_id: 用户ID
        
        Returns:
            使用情况
        """
        if user_id not in self.user_buckets:
            return {
                'limit': self.default_config['user_capacity'],
                'remaining': self.default_config['user_capacity'],
                'used': 0,
            }

        bucket = self.user_buckets[user_id]

        return {
            'limit': bucket.capacity,
            'remaining': max(0, int(bucket.tokens)),
            'used': bucket.capacity - int(bucket.tokens),
        }

    def get_ip_usage(self, ip_address: str) -> Dict[str, any]:
        """
        获取IP使用情况
        
        Args:
            ip_address: IP地址
        
        Returns:
            使用情况
        """
        if ip_address not in self.ip_buckets:
            return {
                'limit': self.default_config['ip_capacity'],
                'remaining': self.default_config['ip_capacity'],
                'used': 0,
            }

        bucket = self.ip_buckets[ip_address]

        return {
            'limit': bucket.capacity,
            'remaining': max(0, int(bucket.tokens)),
            'used': bucket.capacity - int(bucket.tokens),
        }

    def reset_user_limit(self, user_id: int):
        """重置用户限制"""
        if user_id in self.user_buckets:
            del self.user_buckets[user_id]

    def reset_ip_limit(self, ip_address: str):
        """重置IP限制"""
        if ip_address in self.ip_buckets:
            del self.ip_buckets[ip_address]

    def cleanup_expired_buckets(self, max_age: int = 3600):
        """
        清理过期的桶
        
        Args:
            max_age: 最大年龄（秒）
        """
        now = time.time()

        # 清理用户桶
        expired_users = [
            user_id for user_id, bucket in self.user_buckets.items()
            if now - bucket.last_refill > max_age
        ]
        for user_id in expired_users:
            del self.user_buckets[user_id]

        # 清理IP桶
        expired_ips = [
            ip for ip, bucket in self.ip_buckets.items()
            if now - bucket.last_refill > max_age
        ]
        for ip in expired_ips:
            del self.ip_buckets[ip]


# 全局实例
rate_limiter = RateLimiter()

# 导出
__all__ = ['RateLimiter', 'rate_limiter', 'TokenBucket']
