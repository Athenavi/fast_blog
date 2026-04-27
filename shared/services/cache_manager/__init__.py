"""
缓存管理器包
提供多层级缓存服务
"""

from shared.services.cache_manager.asset_minifier import AssetMinifier
from shared.services.cache_manager.lazy_load import LazyLoadService
from shared.services.cache_manager.page_cache import PageCacheService
from shared.services.cache_manager.service import CacheService

# 全局实例
cache_service = CacheService()
page_cache_service = PageCacheService()
lazy_load_service = LazyLoadService()
asset_minifier = AssetMinifier()

__all__ = [
    'CacheService',
    'PageCacheService',
    'LazyLoadService',
    'AssetMinifier',
    'cache_service',
    'page_cache_service',
    'lazy_load_service',
    'asset_minifier',
]
