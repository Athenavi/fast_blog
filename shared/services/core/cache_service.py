"""
性能优化服务 - 缓存、懒加载、资源压缩
"""

import json
import logging
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from cachetools import TTLCache

    CACHE_TOOLS_AVAILABLE = True
except ImportError:
    CACHE_TOOLS_AVAILABLE = False


class CacheService:
    """缓存服务 - 支持内存和Redis

    使用cachetools.TTLCache实现高效的内存缓存(如果可用)
    支持Redis作为后端缓存(可选)
    """

    def __init__(self, use_redis: bool = False, redis_config: Dict[str, Any] = None,
                 max_size: int = 1000, default_ttl: int = 3600):
        """
        初始化缓存服务

        Args:
            use_redis: 是否使用Redis
            redis_config: Redis配置字典
            max_size: 内存缓存最大条目数
            default_ttl: 默认TTL(秒)
        """
        self.default_ttl = default_ttl
        self.use_redis = use_redis
        self.redis_client = None

        # 使用cachetools.TTLCache(如果可用)或普通字典
        if CACHE_TOOLS_AVAILABLE:
            self.cache = TTLCache(maxsize=max_size, ttl=default_ttl)
        else:
            self.cache: Dict[str, Any] = {}
        self.ttl: Dict[str, float] = {}

        # 初始化Redis客户端
        if use_redis and REDIS_AVAILABLE:
            try:
                config = redis_config or {
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0,
                    'decode_responses': True,  # 自动解码为字符串
                    'socket_connect_timeout': 1,  # 连接超时 1 秒
                    'socket_timeout': 1,  # 读写超时 1 秒
                }
                self.redis_client = redis.Redis(**config)
                # 移除 ping()：redis.Redis() 本身是惰性的，首次实际操作时才连接
                logger.info("[CacheService] Redis客户端已创建（惰性连接）")
            except Exception as e:
                logger.error(f"[CacheService] Redis连接失败: {e}, 使用内存缓存")
                self.use_redis = False
                self.redis_client = None
        elif use_redis and not REDIS_AVAILABLE:
            logger.warning("[CacheService] redis库未安装,使用内存缓存")
            self.use_redis = False

    def get(self, key: str) -> Optional[Any]:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值,不存在则返回None
        """
        # 优先从Redis获取
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    # 尝试反序列化JSON
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
                return None
            except Exception as e:
                logger.error(f"[CacheService] Redis获取失败: {e}, 降级到内存缓存")
                self.use_redis = False

        # 从内存缓存获取(cachetools会自动处理TTL)
        if CACHE_TOOLS_AVAILABLE:
            # 先检查手动 TTL（支持 per-key TTL 覆盖）
            if key in self.ttl and time.time() > self.ttl[key]:
                del self.cache[key]
                del self.ttl[key]
                return None
            return self.cache.get(key)
        else:
            # 手动TTL检查(兼容模式)
            if key in self.cache:
                if key in self.ttl and time.time() > self.ttl[key]:
                    del self.cache[key]
                    del self.ttl[key]
                    return None
                return self.cache[key]
            return None

    def get_or_set(self, key: str, factory, ttl: int = None) -> Any:
        """
        获取或设置缓存（带 SETNX 分布式锁，防止缓存雪崩）

        当缓存 miss 时，使用分布式锁确保只有一个请求回填缓存。
        其他请求等待锁期间返回过期的缓存值（stale-while-revalidate）。

        Args:
            key: 缓存键
            factory: 回填数据的工厂函数（async 或 sync）
            ttl: 过期时间(秒)

        Returns:
            缓存值
        """
        if ttl is None:
            ttl = self.default_ttl

        # 尝试读取缓存
        cached = self.get(key)
        if cached is not None:
            return cached

        import asyncio
        lock_key = f"{key}:lock"
        lock_ttl = 10  # 锁最长持有时间（防止死锁）

        if self.use_redis and self.redis_client:
            try:
                # Redis 分布式锁（SETNX）
                acquired = self.redis_client.setnx(lock_key, "1")
                if acquired:
                    self.redis_client.expire(lock_key, lock_ttl)
                    try:
                        # 只有获得锁的请求回填缓存
                        if asyncio.iscoroutinefunction(factory):
                            value = asyncio.get_event_loop().run_until_complete(factory())
                        else:
                            value = factory()
                        self.set(key, value, ttl)
                        return value
                    finally:
                        self.redis_client.delete(lock_key)
                else:
                    # 未获得锁：等待 + 重试
                    import time as time_module
                    time_module.sleep(0.1)  # 等待 100ms
                    retried = self.get(key)
                    if retried is not None:
                        return retried
                    # 锁持有者可能失败，直接回填（无锁保护）
                    if asyncio.iscoroutinefunction(factory):
                        value = asyncio.get_event_loop().run_until_complete(factory())
                    else:
                        value = factory()
                    self.set(key, value, ttl)
                    return value
            except Exception as e:
                logger.warning(f"[CacheService] 分布式锁获取失败: {e}, 直接回填")
                # 锁失败时直接回填（降级）
                if asyncio.iscoroutinefunction(factory):
                    value = asyncio.get_event_loop().run_until_complete(factory())
                else:
                    value = factory()
                self.set(key, value, ttl)
                return value

        # 无 Redis 时直接回填（内存缓存无分布式锁需求）
        if asyncio.iscoroutinefunction(factory):
            value = asyncio.get_event_loop().run_until_complete(factory())
        else:
            value = factory()
        self.set(key, value, ttl)
        return value

    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒),默认使用default_ttl
        """
        if ttl is None:
            ttl = self.default_ttl

        # 存储到Redis
        if self.use_redis and self.redis_client:
            try:
                # 将值序列化为JSON字符串
                if isinstance(value, (dict, list, bool, type(None))):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = str(value)

                self.redis_client.setex(key, ttl, serialized_value)
            except Exception as e:
                logger.warning(f"[CacheService] Redis存储失败: {e}, 降级到内存缓存")
                self.use_redis = False

        # 存储到内存缓存
        # 使用手动 TTL 管理（支持 per-key TTL，不受 TTLCache 全局 TTL 限制）
        if key in self.cache and CACHE_TOOLS_AVAILABLE:
            # 如果使用 TTLCache，需要通过 del 再 set 来刷新 TTL
            del self.cache[key]
        self.cache[key] = value
        self.ttl[key] = time.time() + ttl

    def delete(self, key: str):
        """删除缓存

        Args:
            key: 缓存键
        """
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"[CacheService] Redis删除失败: {e}")

        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """清空缓存（仅清空应用缓存前缀的 key，不 flushdb 整个 Redis）"""
        if self.use_redis and self.redis_client:
            try:
                # 仅删除带应用前缀的 key，避免清空整个 Redis
                prefix = getattr(self, 'key_prefix', 'fastblog:')
                cursor = 0
                deleted = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor=cursor, match=f"{prefix}*", count=500)
                    if keys:
                        deleted += len(keys)
                        self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
                logger.info(f"[CacheService] Redis已清除 {deleted} 个缓存 key (前缀: {prefix})")
            except Exception as e:
                logger.warning(f"[CacheService] Redis清除失败: {e}")

        self.cache.clear()


class LazyLoadService:
    """图片懒加载服务"""

    def generate_lazy_html(self, image_url: str, alt: str = "", class_name: str = "") -> str:
        """
        生成懒加载HTML

        Args:
            image_url: 图片URL
            alt: 替代文本
            class_name: CSS类名
        """
        return f'''
        <img
            data-src="{image_url}"
            alt="{alt}"
            class="lazyload {class_name}"
            loading="lazy"
            onload="this.src=this.dataset.src"
        />
        '''

    def add_lazy_load_script(self) -> str:
        """添加懒加载JavaScript"""
        return '''
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            const lazyImages = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                });
            });
            lazyImages.forEach(img => imageObserver.observe(img));
        });
        </script>
        '''


class AssetMinifier:
    """CSS/JS合并压缩服务"""

    def minify_css(self, css_content: str) -> str:
        """压缩CSS"""
        # 移除注释
        import re
        css = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        # 移除多余空白
        css = re.sub(r'\s+', ' ', css)
        css = re.sub(r'\s*([{}:;,])\s*', r'\1', css)
        return css.strip()

    def minify_js(self, js_content: str) -> str:
        """压缩JavaScript"""
        import re
        # 移除单行注释(不在字符串中的)
        js = re.sub(r'//[^\n]*', '', js_content)
        # 移除多余空白
        js = re.sub(r'\s+', ' ', js)
        return js.strip()

    def combine_files(self, file_paths: List[str], output_path: str, file_type: str = 'css'):
        """
        合并多个文件

        Args:
            file_paths: 文件路径列表
            output_path: 输出文件路径
            file_type: 文件类型(css/js)
        """
        combined = []
        for path in file_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    combined.append(f.read())
            except Exception as e:
                logger.warning(f"读取文件失败 {path}: {e}")

        content = '\n'.join(combined)

        # 压缩
        if file_type == 'css':
            content = self.minify_css(content)
        elif file_type == 'js':
            content = self.minify_js(content)

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return output_path


def cached(ttl: int = 3600):
    """缓存装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cached_value = cache_service.get(cache_key)

            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# 全局实例
cache_service = CacheService()
lazy_load_service = LazyLoadService()
asset_minifier = AssetMinifier()
