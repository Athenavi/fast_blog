"""
页面缓存插件
页面级缓存系统，提升网站访问速度
"""

import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class PageCachePlugin(BasePlugin):
    """
    页面缓存插件
    
    功能:
    1. 页面静态化缓存
    2. 缓存过期策略
    3. 缓存清理机制
    4. 缓存预热
    5. 缓存命中率统计
    6. 选择性缓存规则
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="页面缓存",
            slug="page-cache",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_cache': True,
            'default_ttl': 3600,  # 默认缓存时间(秒)，1小时
            'max_cache_size': 1000,  # 最大缓存条目数
            'cache_path': 'storage/cache/page_cache',  # 缓存存储路径
            'enable_compression': True,  # 启用压缩
            'cache_logged_in': False,  # 是否缓存登录用户页面
            'excluded_paths': ['/admin', '/api', '/login', '/register'],  # 排除的路径
            'cache_query_strings': False,  # 是否区分查询字符串
            'auto_clear_on_update': True,  # 内容更新时自动清除缓存
        }

        # 内存缓存 {cache_key: {'data': ..., 'timestamp': ..., 'ttl': ...}}
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

        # 缓存统计
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'deletes': 0,
            'total_requests': 0,
        }

        # 初始化缓存目录
        self._init_cache_dir()

    def register_hooks(self):
        """注册钩子"""
        # 请求前检查缓存
        plugin_hooks.add_filter(
            "before_response",
            self.serve_cached_page,
            priority=1
        )

        # 响应后保存缓存
        plugin_hooks.add_action(
            "after_response",
            self.cache_page,
            priority=10
        )

        # 文章发布/更新时清除相关缓存
        plugin_hooks.add_action(
            "article_published",
            self.on_content_update,
            priority=10
        )
        
        plugin_hooks.add_action(
            "article_updated",
            self.on_content_update,
            priority=10
        )

        plugin_hooks.add_action(
            "article_deleted",
            self.on_content_update,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        self._init_cache_dir()
        print(f"[PageCache] Plugin activated - Cache enabled")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[PageCache] Plugin deactivated")

    def serve_cached_page(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提供缓存的页面
        
        Args:
            request_data: 请求数据 {url, method, headers, user_id, query_params}
            
        Returns:
            如果有缓存返回 {cached: True, data: ...}，否则返回 {cached: False}
        """
        if not self.settings.get('enable_cache'):
            return {'cached': False}

        # 检查是否应该缓存此请求
        if not self._should_cache_request(request_data):
            return {'cached': False}

        # 生成缓存键
        cache_key = self._generate_cache_key(request_data)

        # 尝试从内存缓存获取
        cached_data = self._get_from_memory(cache_key)
        
        if cached_data:
            self.stats['hits'] += 1
            self.stats['total_requests'] += 1
            print(f"[PageCache] Cache HIT (memory): {request_data.get('url')}")
            return {
                'cached': True,
                'data': cached_data,
                'source': 'memory',
            }

        # 尝试从文件缓存获取
        cached_data = self._get_from_file(cache_key)
        
        if cached_data:
            self.stats['hits'] += 1
            self.stats['total_requests'] += 1
            
            # 加载到内存缓存
            ttl = self.settings.get('default_ttl', 3600)
            self._save_to_memory(cache_key, cached_data, ttl)
            
            print(f"[PageCache] Cache HIT (file): {request_data.get('url')}")
            return {
                'cached': True,
                'data': cached_data,
                'source': 'file',
            }

        # 缓存未命中
        self.stats['misses'] += 1
        self.stats['total_requests'] += 1
        print(f"[PageCache] Cache MISS: {request_data.get('url')}")
        return {'cached': False}

    def cache_page(self, response_data: Dict[str, Any]):
        """
        缓存页面
        
        Args:
            response_data: 响应数据 {url, status_code, headers, body, request_data}
        """
        if not self.settings.get('enable_cache'):
            return

        request_data = response_data.get('request_data', {})
        
        # 检查是否应该缓存
        if not self._should_cache_response(response_data):
            return

        # 生成缓存键
        cache_key = self._generate_cache_key(request_data)

        # 准备缓存数据
        cache_entry = {
            'url': response_data.get('url'),
            'status_code': response_data.get('status_code', 200),
            'headers': response_data.get('headers', {}),
            'body': response_data.get('body'),
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(seconds=self.settings.get('default_ttl', 3600))).isoformat(),
        }

        # 保存到内存缓存
        ttl = self.settings.get('default_ttl', 3600)
        self._save_to_memory(cache_key, cache_entry, ttl)

        # 保存到文件缓存
        self._save_to_file(cache_key, cache_entry)

        self.stats['writes'] += 1
        print(f"[PageCache] Cached: {response_data.get('url')}")

    def clear_cache(self, pattern: str = None):
        """
        清除缓存
        
        Args:
            pattern: 缓存键模式，如果为None则清除所有缓存
        """
        cleared_count = 0

        if pattern:
            # 清除匹配的缓存
            keys_to_delete = [
                key for key in self.memory_cache.keys()
                if pattern in key
            ]
            for key in keys_to_delete:
                del self.memory_cache[key]
                cleared_count += 1
            
            # 清除文件缓存
            self._clear_file_cache(pattern)
        else:
            # 清除所有缓存
            self.memory_cache.clear()
            cleared_count = len(self.memory_cache)
            self._clear_all_file_cache()

        self.stats['deletes'] += cleared_count
        print(f"[PageCache] Cleared {cleared_count} cache entries")

    def on_content_update(self, content_data: Dict[str, Any]):
        """
        内容更新时的处理
        
        Args:
            content_data: 内容数据 {type, id, url}
        """
        if not self.settings.get('auto_clear_on_update'):
            return

        # 清除相关页面的缓存
        content_type = content_data.get('type', 'article')
        content_id = content_data.get('id')
        content_url = content_data.get('url', '')

        # 清除特定URL的缓存
        if content_url:
            self.clear_cache(content_url)
        
        # 清除首页和列表页缓存
        self.clear_cache('/')
        self.clear_cache('/articles')
        self.clear_cache(f'/{content_type}')
        
        print(f"[PageCache] Auto-cleared cache for {content_type} #{content_id}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计数据
        """
        total_requests = self.stats['total_requests']
        hits = self.stats['hits']
        misses = self.stats['misses']
        
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        # 计算缓存大小
        memory_cache_size = len(self.memory_cache)
        file_cache_size = self._get_file_cache_size()
        
        return {
            'enabled': self.settings.get('enable_cache'),
            'total_requests': total_requests,
            'cache_hits': hits,
            'cache_misses': misses,
            'cache_writes': self.stats['writes'],
            'cache_deletes': self.stats['deletes'],
            'hit_rate': round(hit_rate, 2),
            'memory_cache_entries': memory_cache_size,
            'file_cache_entries': file_cache_size,
            'total_cache_entries': memory_cache_size + file_cache_size,
            'max_cache_size': self.settings.get('max_cache_size'),
            'default_ttl': self.settings.get('default_ttl'),
            'settings': self.settings,
        }

    def warmup_cache(self, urls: List[str]):
        """
        预热缓存
        
        Args:
            urls: 需要预热的URL列表
        """
        print(f"[PageCache] Starting cache warmup for {len(urls)} URLs")
        
        warmed_count = 0
        for url in urls:
            # 模拟请求以触发缓存
            request_data = {
                'url': url,
                'method': 'GET',
                'headers': {},
                'user_id': None,
                'query_params': {},
            }
            
            # 这里应该实际发起HTTP请求获取页面内容
            # 简化实现：标记为已预热
            cache_key = self._generate_cache_key(request_data)
            self.memory_cache[cache_key] = {
                'data': {'url': url, 'warmed': True},
                'timestamp': time.time(),
                'ttl': self.settings.get('default_ttl', 3600),
            }
            warmed_count += 1
        
        print(f"[PageCache] Warmed up {warmed_count} pages")

    def _should_cache_request(self, request_data: Dict[str, Any]) -> bool:
        """判断是否应该缓存此请求"""
        # 检查是否启用缓存
        if not self.settings.get('enable_cache'):
            return False

        # 只缓存GET请求
        if request_data.get('method', 'GET').upper() != 'GET':
            return False

        url = request_data.get('url', '')

        # 检查排除的路径
        excluded_paths = self.settings.get('excluded_paths', [])
        for excluded in excluded_paths:
            if url.startswith(excluded):
                return False

        # 检查登录用户
        if not self.settings.get('cache_logged_in') and request_data.get('user_id'):
            return False

        return True

    def _should_cache_response(self, response_data: Dict[str, Any]) -> bool:
        """判断是否应该缓存此响应"""
        # 只缓存成功的响应
        status_code = response_data.get('status_code', 200)
        if status_code != 200:
            return False

        # 不缓存空内容
        if not response_data.get('body'):
            return False

        return True

    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            request_data: 请求数据
            
        Returns:
            缓存键
        """
        url = request_data.get('url', '')
        
        # 如果不区分查询字符串，去掉查询参数
        if not self.settings.get('cache_query_strings'):
            url = url.split('?')[0]
        
        # 添加用户ID（如果缓存登录用户）
        user_id = request_data.get('user_id', 'anonymous')
        
        # 生成唯一键
        key_string = f"{user_id}:{url}"
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return cache_key

    def _get_from_memory(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从内存缓存获取"""
        if cache_key not in self.memory_cache:
            return None

        cache_entry = self.memory_cache[cache_key]
        current_time = time.time()

        # 检查是否过期
        if current_time - cache_entry['timestamp'] > cache_entry['ttl']:
            del self.memory_cache[cache_key]
            return None

        return cache_entry['data']

    def _save_to_memory(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """保存到内存缓存"""
        # 检查缓存大小限制
        max_size = self.settings.get('max_cache_size', 1000)
        if len(self.memory_cache) >= max_size:
            # 删除最旧的缓存
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]['timestamp']
            )
            del self.memory_cache[oldest_key]

        self.memory_cache[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl,
        }

    def _get_from_file(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从文件缓存获取"""
        cache_file = self._get_cache_file_path(cache_key)
        
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)

            # 检查是否过期
            expires_at = datetime.fromisoformat(cache_entry.get('expires_at', ''))
            if datetime.now() > expires_at:
                cache_file.unlink()
                return None

            return cache_entry

        except Exception as e:
            print(f"[PageCache] Failed to read cache file: {e}")
            return None

    def _save_to_file(self, cache_key: str, data: Dict[str, Any]):
        """保存到文件缓存"""
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            # 创建子目录
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入缓存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[PageCache] Failed to write cache file: {e}")

    def _clear_file_cache(self, pattern: str = None):
        """清除文件缓存"""
        cache_dir = Path(self.settings.get('cache_path', 'storage/cache/page_cache'))
        
        if not cache_dir.exists():
            return

        cleared = 0
        for cache_file in cache_dir.rglob('*.json'):
            if pattern is None or pattern in str(cache_file):
                cache_file.unlink()
                cleared += 1

        print(f"[PageCache] Cleared {cleared} file cache entries")

    def _clear_all_file_cache(self):
        """清除所有文件缓存"""
        cache_dir = Path(self.settings.get('cache_path', 'storage/cache/page_cache'))
        
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            self._init_cache_dir()

    def _get_file_cache_size(self) -> int:
        """获取文件缓存数量"""
        cache_dir = Path(self.settings.get('cache_path', 'storage/cache/page_cache'))
        
        if not cache_dir.exists():
            return 0

        return len(list(cache_dir.rglob('*.json')))

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        cache_dir = Path(self.settings.get('cache_path', 'storage/cache/page_cache'))
        # 使用子目录避免单个目录文件过多
        subdir = cache_key[:2]
        return cache_dir / subdir / f"{cache_key}.json"

    def _init_cache_dir(self):
        """初始化缓存目录"""
        cache_dir = Path(self.settings.get('cache_path', 'storage/cache/page_cache'))
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"[PageCache] Cache directory initialized: {cache_dir}")

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_cache',
                    'type': 'boolean',
                    'label': '启用页面缓存',
                },
                {
                    'key': 'default_ttl',
                    'type': 'number',
                    'label': '默认缓存时间（秒）',
                    'min': 60,
                    'max': 86400,
                    'help': '缓存的有效期',
                },
                {
                    'key': 'max_cache_size',
                    'type': 'number',
                    'label': '最大缓存条目数',
                    'min': 100,
                    'max': 10000,
                    'help': '内存缓存的最大条目数',
                },
                {
                    'key': 'cache_logged_in',
                    'type': 'boolean',
                    'label': '缓存登录用户页面',
                    'help': '警告：可能导致数据泄露',
                },
                {
                    'key': 'cache_query_strings',
                    'type': 'boolean',
                    'label': '区分查询字符串',
                    'help': '为不同的查询参数生成不同缓存',
                },
                {
                    'key': 'auto_clear_on_update',
                    'type': 'boolean',
                    'label': '内容更新时自动清除缓存',
                },
                {
                    'key': 'excluded_paths',
                    'type': 'text',
                    'label': '排除的路径（逗号分隔）',
                    'help': '这些路径不会被缓存',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看缓存统计',
                    'action': 'view_stats',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '清除所有缓存',
                    'action': 'clear_all',
                    'variant': 'danger',
                },
                {
                    'type': 'button',
                    'label': '预热缓存',
                    'action': 'warmup',
                    'variant': 'primary',
                },
            ]
        }


# 插件实例
plugin_instance = PageCachePlugin()
