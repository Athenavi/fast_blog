"""
CDN管理插件
集成主流CDN服务商，提供缓存管理和性能优化
"""

from typing import Dict, List, Any

import aiohttp

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class CDNManagerPlugin(BasePlugin):
    """
    CDN管理插件
    
    功能:
    1. 多CDN服务商支持(Cloudflare, KeyCDN等)
    2. 自动缓存刷新
    3. 手动缓存清除
    4. CDN状态监控
    5. 性能分析报告
    6. 资源URL重写
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="CDN管理",
            slug="cdn-manager",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'provider': 'cloudflare',
            'api_key': '',
            'zone_id': '',
            'cdn_domain': '',
            'auto_purge': True,
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章发布/更新时刷新CDN缓存
        if self.settings.get('auto_purge', True):
            plugin_hooks.add_action(
                "article_published",
                self.on_content_updated,
                priority=5
            )
            plugin_hooks.add_action(
                "article_updated",
                self.on_content_updated,
                priority=5
            )

        # URL过滤器 - 重写资源URL为CDN地址
        plugin_hooks.add_filter(
            "media_url",
            self.rewrite_media_url,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        self._validate_config()

    def _validate_config(self):
        """验证CDN配置"""
        if not self.settings.get('api_key'):
            print("[CDNManager] Warning: API key not configured")

        if self.settings['provider'] == 'cloudflare' and not self.settings.get('zone_id'):
            print("[CDNManager] Warning: Cloudflare Zone ID not configured")

    async def on_content_updated(self, content_data: Dict[str, Any]):
        """内容更新时刷新CDN缓存"""
        article_id = content_data.get('id')
        if not article_id:
            return

        # 生成需要刷新的URL列表
        urls_to_purge = [
            f"/articles/{article_id}",
            f"/p/{content_data.get('slug', '')}",
            "/",  # 首页
            "/sitemap.xml",
        ]

        await self.purge_cache(urls=urls_to_purge)

    async def purge_cache(
            self,
            urls: List[str] = None,
            tags: List[str] = None,
            purge_all: bool = False,
    ) -> Dict[str, Any]:
        """
        刷新CDN缓存
        
        Args:
            urls: 需要刷新的URL列表
            tags: 缓存标签(部分CDN支持)
            purge_all: 是否清除所有缓存
            
        Returns:
            刷新结果
        """
        provider = self.settings.get('provider', 'cloudflare')

        try:
            if provider == 'cloudflare':
                return await self._purge_cloudflare(urls, tags, purge_all)
            elif provider == 'keycdn':
                return await self._purge_keycdn(urls, purge_all)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported CDN provider: {provider}',
                }

        except Exception as e:
            print(f"[CDNManager] Failed to purge cache: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    async def _purge_cloudflare(
            self,
            urls: List[str] = None,
            tags: List[str] = None,
            purge_all: bool = False,
    ) -> Dict[str, Any]:
        """Cloudflare缓存刷新"""
        api_key = self.settings.get('api_key')
        zone_id = self.settings.get('zone_id')

        if not api_key or not zone_id:
            return {
                'success': False,
                'error': 'Cloudflare API key or Zone ID not configured',
            }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        # 构建请求数据
        if purge_all:
            data = {'purge_everything': True}
        else:
            data = {'files': urls or []}
            if tags:
                data['tags'] = tags

        # 发送API请求
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()

                if result.get('success'):
                    print(f"[CDNManager] Cloudflare cache purged successfully")
                    return {
                        'success': True,
                        'data': {
                            'provider': 'cloudflare',
                            'purged_urls': len(urls) if urls else 0,
                            'purge_all': purge_all,
                        }
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    return {
                        'success': False,
                        'error': error_msg,
                    }

    async def _purge_keycdn(
            self,
            urls: List[str] = None,
            purge_all: bool = False,
    ) -> Dict[str, Any]:
        """KeyCDN缓存刷新"""
        api_key = self.settings.get('api_key')

        if not api_key:
            return {
                'success': False,
                'error': 'KeyCDN API key not configured',
            }

        headers = {
            'Api-Key': api_key,
            'Content-Type': 'application/json',
        }

        # KeyCDN使用不同的API端点
        cdn_domain = self.settings.get('cdn_domain', '').replace('https://', '').replace('http://', '')

        if purge_all:
            # KeyCDN不支持全部清除,需要逐个URL
            if not urls:
                return {
                    'success': False,
                    'error': 'KeyCDN requires specific URLs to purge',
                }

        # 构建URL列表
        full_urls = [
            f"https://{cdn_domain}{url}" if not url.startswith('http') else url
            for url in (urls or [])
        ]

        data = {'urls': full_urls}

        url = "https://api.keycdn.com/zones/purge.json"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()

                if response.status == 200:
                    print(f"[CDNManager] KeyCDN cache purged successfully")
                    return {
                        'success': True,
                        'data': {
                            'provider': 'keycdn',
                            'purged_urls': len(full_urls),
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Failed to purge cache'),
                    }

    def rewrite_media_url(self, url: str) -> str:
        """
        重写媒体URL为CDN地址
        
        Args:
            url: 原始URL
            
        Returns:
            CDN URL
        """
        cdn_domain = self.settings.get('cdn_domain')

        if not cdn_domain:
            return url

        # 只重写本地资源
        if url.startswith('/storage/') or url.startswith('/media/'):
            # 确保CDN域名有协议
            if not cdn_domain.startswith('http'):
                cdn_domain = f"https://{cdn_domain}"

            # 拼接CDN URL
            return f"{cdn_domain}{url}"

        return url

    async def get_cdn_stats(self) -> Dict[str, Any]:
        """获取CDN统计信息"""
        provider = self.settings.get('provider', 'cloudflare')

        try:
            if provider == 'cloudflare':
                return await self._get_cloudflare_stats()
            else:
                return {
                    'success': False,
                    'error': f'Stats not available for {provider}',
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    async def _get_cloudflare_stats(self) -> Dict[str, Any]:
        """获取Cloudflare统计"""
        api_key = self.settings.get('api_key')
        zone_id = self.settings.get('zone_id')

        if not api_key or not zone_id:
            return {
                'success': False,
                'error': 'Cloudflare not configured',
            }

        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        # 获取带宽和请求统计
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/analytics/dashboard"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                result = await response.json()

                if result.get('success'):
                    analytics = result.get('result', {})
                    return {
                        'success': True,
                        'data': {
                            'provider': 'cloudflare',
                            'bandwidth': analytics.get('totals', {}).get('bandwidth', 0),
                            'requests': analytics.get('totals', {}).get('requests', 0),
                            'cached_requests': analytics.get('totals', {}).get('cachedRequests', 0),
                            'cache_hit_ratio': analytics.get('totals', {}).get('cacheHitRatio', 0),
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to fetch stats',
                    }

    async def test_connection(self) -> Dict[str, Any]:
        """测试CDN连接"""
        provider = self.settings.get('provider', 'cloudflare')

        try:
            if provider == 'cloudflare':
                api_key = self.settings.get('api_key')
                zone_id = self.settings.get('zone_id')

                if not api_key or not zone_id:
                    return {
                        'success': False,
                        'error': 'Missing API key or Zone ID',
                    }

                headers = {
                    'Authorization': f'Bearer {api_key}',
                }

                url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        result = await response.json()

                        if result.get('success'):
                            zone_info = result.get('result', {})
                            return {
                                'success': True,
                                'data': {
                                    'message': 'Connection successful',
                                    'zone_name': zone_info.get('name'),
                                    'status': zone_info.get('status'),
                                }
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'Authentication failed',
                            }

            return {
                'success': False,
                'error': f'Test not implemented for {provider}',
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'provider',
                    'type': 'select',
                    'label': 'CDN服务商',
                    'options': [
                        {'value': 'cloudflare', 'label': 'Cloudflare'},
                        {'value': 'keycdn', 'label': 'KeyCDN'},
                        {'value': 'custom', 'label': '自定义'},
                    ],
                    'help': '选择您的CDN服务提供商',
                },
                {
                    'key': 'api_key',
                    'type': 'password',
                    'label': 'API密钥',
                    'placeholder': '输入API密钥',
                    'help': '从CDN服务商控制台获取',
                },
                {
                    'key': 'zone_id',
                    'type': 'text',
                    'label': 'Zone ID',
                    'placeholder': 'Cloudflare Zone ID',
                    'help': '仅Cloudflare需要',
                    'conditional': {'provider': 'cloudflare'},
                },
                {
                    'key': 'cdn_domain',
                    'type': 'text',
                    'label': 'CDN域名',
                    'placeholder': 'cdn.example.com',
                    'help': '您的CDN加速域名',
                },
                {
                    'key': 'auto_purge',
                    'type': 'boolean',
                    'label': '自动刷新缓存',
                    'help': '内容更新时自动刷新CDN缓存',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '测试连接',
                    'action': 'test_connection',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '清除所有缓存',
                    'action': 'purge_all',
                    'variant': 'destructive',
                    'confirm': '确定要清除所有CDN缓存吗?',
                },
            ]
        }


# 插件实例
plugin_instance = CDNManagerPlugin()
