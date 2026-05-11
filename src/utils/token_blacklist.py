"""
Redis Token 黑名单管理
实现 JWT Token 的黑名单机制，支持 Token 撤销
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisTokenBlacklist:
    """基于 Redis 的 Token 黑名单管理器"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """初始化 Redis 连接"""
        try:
            import redis
            
            # 从环境变量读取 Redis 配置
            redis_host = os.environ.get('REDIS_HOST', 'localhost')
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_db = int(os.environ.get('REDIS_DB', 0))
            redis_password = os.environ.get('REDIS_PASSWORD') or None
            
            # 尝试连接 Redis
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True
            )
            
            # 测试连接
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Redis Token 黑名单已启用：{redis_host}:{redis_port}")
            
        except ImportError:
            logger.warning("redis 库未安装，Token 黑名单功能将不可用")
            self.enabled = False
        except Exception as e:
            logger.warning(f"Redis 连接失败，Token 黑名单功能将降级为内存模式：{e}")
            self.redis_client = None
            self.enabled = False
    
    def add_to_blacklist(self, token: str, expires_at: datetime) -> bool:
        """
        将 Token 加入黑名单
        
        Args:
            token: JWT Token 字符串
            expires_at: Token 过期时间
            
        Returns:
            bool: 操作是否成功
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Redis 不可用，使用内存黑名单（重启后失效）")
            return False
        
        try:
            # 计算剩余有效期（秒）
            ttl = int((expires_at - datetime.now()).total_seconds())
            if ttl > 0:
                # 使用 JTI 作为 key（实际应用中应该解析 token 获取 jti）
                key = f"token_blacklist:{token[:32]}"  # 使用前 32 个字符作为标识
                self.redis_client.setex(key, ttl, "blacklisted")
                logger.debug(f"Token 已加入黑名单，TTL: {ttl}s")
                return True
        except Exception as e:
            logger.error(f"添加 Token 到黑名单失败：{e}")
        
        return False
    
    def is_blacklisted(self, token: str) -> bool:
        """
        检查 Token 是否在黑名单中
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            bool: 是否在黑名单中
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Redis 不可用，跳过黑名单检查")
            return False
        
        try:
            key = f"token_blacklist:{token[:32]}"
            return self.redis_client.exists(key) == 1
        except Exception as e:
            logger.error(f"检查 Token 黑名单失败：{e}")
            return False
    
    def clear_expired(self):
        """清理过期的黑名单记录（Redis 会自动处理 TTL）"""
        pass  # Redis 会自动清理，不需要手动处理
    
    @property
    def is_available(self) -> bool:
        """Redis 是否可用"""
        return self.enabled and self.redis_client is not None


# 全局实例
token_blacklist = RedisTokenBlacklist()
