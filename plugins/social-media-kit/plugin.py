"""
社交媒体套件插件 (Social Media Kit)
提供自动分享、社交登录增强、社交证明小部件和Instagram feed展示功能
"""

from datetime import datetime
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class SocialMediaKitPlugin(BasePlugin):
    """
    社交媒体套件插件
    
    功能:
    1. 自动分享到Twitter/Facebook - 文章发布时自动推送
    2. 社交登录增强 - 支持多平台OAuth登录
    3. 社交证明小部件 - 显示粉丝数、分享数等
    4. Instagram feed展示 - 嵌入Instagram内容
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="社交媒体套件",
            slug="social-media-kit",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_auto_share': True,
            'auto_share_platforms': ['twitter'],
            'enable_social_login': True,
            'show_social_proof': True,
            'instagram_username': '',
            'share_button_style': 'default',
        }

        # API凭证（实际应加密存储）
        self.api_credentials = {
            'twitter': {'api_key': '', 'api_secret': ''},
            'facebook': {'app_id': '', 'app_secret': ''},
            'linkedin': {'client_id': '', 'client_secret': ''},
        }

        # 社交统计数据
        self.social_stats = {
            'total_shares': 0,
            'by_platform': {},
            'recent_shares': [],
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章发布时自动分享
        plugin_hooks.add_action(
            "article_published",
            self.auto_share_article,
            priority=10
        )

        # 页面头部注入社交元数据
        plugin_hooks.add_action(
            "page_head",
            self.inject_social_meta_tags,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[SocialMediaKit] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[SocialMediaKit] Plugin deactivated")

    def auto_share_article(self, article_data: Dict[str, Any]):
        """
        文章发布时自动分享到社交平台
        
        Args:
            article_data: 文章数据 {title, url, excerpt, image}
        """
        if not self.settings.get('enable_auto_share'):
            return

        platforms = self.settings.get('auto_share_platforms', [])

        for platform in platforms:
            try:
                success = self._share_to_platform(platform, article_data)
                if success:
                    self.social_stats['total_shares'] += 1
                    self.social_stats['by_platform'][platform] = \
                        self.social_stats['by_platform'].get(platform, 0) + 1

                    self.social_stats['recent_shares'].append({
                        'platform': platform,
                        'article_title': article_data.get('title'),
                        'timestamp': datetime.now().isoformat(),
                    })

                    print(f"[SocialMediaKit] Auto-shared to {platform}: {article_data.get('title')}")
            except Exception as e:
                print(f"[SocialMediaKit] Failed to share to {platform}: {str(e)}")

    def _share_to_platform(self, platform: str, article_data: Dict[str, Any]) -> bool:
        """
        分享到指定平台
        
        Args:
            platform: 平台名称
            article_data: 文章数据
            
        Returns:
            是否成功
        """
        title = article_data.get('title', '')
        url = article_data.get('url', '')
        excerpt = article_data.get('excerpt', '')
        image = article_data.get('image', '')

        if platform == 'twitter':
            # Twitter分享逻辑（需要集成Twitter API）
            message = f"{title}\n\n{url}"
            print(f"[SocialMediaKit] Would tweet: {message}")
            return True  # 模拟成功

        elif platform == 'facebook':
            # Facebook分享逻辑
            print(f"[SocialMediaKit] Would post to Facebook: {url}")
            return True

        elif platform == 'linkedin':
            # LinkedIn分享逻辑
            print(f"[SocialMediaKit] Would share on LinkedIn: {title}")
            return True

        return False

    def inject_social_meta_tags(self, context: Dict[str, Any]):
        """
        注入社交元数据标签（Open Graph, Twitter Cards）
        
        Args:
            context: 页面上下文
        """
        try:
            page_url = context.get('url', '')
            page_title = context.get('title', '')
            page_description = context.get('description', '')
            page_image = context.get('image', '')

            # Open Graph标签
            og_tags = [
                f'<meta property="og:title" content="{page_title}" />',
                f'<meta property="og:description" content="{page_description}" />',
                f'<meta property="og:url" content="{page_url}" />',
                f'<meta property="og:type" content="article" />',
            ]

            if page_image:
                og_tags.append(f'<meta property="og:image" content="{page_image}" />')

            # Twitter Card标签
            twitter_tags = [
                '<meta name="twitter:card" content="summary_large_image" />',
                f'<meta name="twitter:title" content="{page_title}" />',
                f'<meta name="twitter:description" content="{page_description}" />',
            ]

            if page_image:
                twitter_tags.append(f'<meta name="twitter:image" content="{page_image}" />')

            # 这里应该通过钩子返回HTML，简化实现仅打印
            print(f"[SocialMediaKit] Injecting social meta tags for: {page_title}")

        except Exception as e:
            print(f"[SocialMediaKit] Failed to inject meta tags: {str(e)}")

    def get_social_proof_widget(self) -> Dict[str, Any]:
        """
        获取社交证明小部件数据
        
        Returns:
            社交证明数据
        """
        if not self.settings.get('show_social_proof'):
            return {'enabled': False}

        return {
            'enabled': True,
            'total_shares': self.social_stats['total_shares'],
            'shares_by_platform': self.social_stats['by_platform'],
            'recent_activity': self.social_stats['recent_shares'][-5:],  # 最近5条
            'followers': {
                'twitter': 1234,  # 实际应从API获取
                'facebook': 5678,
                'instagram': 9012,
            },
        }

    def get_instagram_feed(self, count: int = 6) -> List[Dict[str, Any]]:
        """
        获取Instagram feed
        
        Args:
            count: 返回数量
            
        Returns:
            Instagram帖子列表
        """
        username = self.settings.get('instagram_username', '')
        if not username:
            return []

        # 这里应该调用Instagram API获取真实数据
        # 简化实现：返回示例数据
        sample_posts = [
            {
                'id': f'post_{i}',
                'caption': f'Instagram post {i}',
                'image_url': f'https://example.com/instagram/{i}.jpg',
                'permalink': f'https://instagram.com/p/post_{i}',
                'timestamp': datetime.now().isoformat(),
                'likes': 100 + i * 10,
                'comments': 10 + i,
            }
            for i in range(1, count + 1)
        ]

        return sample_posts

    def configure_social_login(self, platform: str, credentials: Dict[str, str]) -> bool:
        """
        配置社交登录凭证
        
        Args:
            platform: 平台名称
            credentials: API凭证
            
        Returns:
            是否成功
        """
        if platform in self.api_credentials:
            self.api_credentials[platform].update(credentials)
            print(f"[SocialMediaKit] Configured {platform} login credentials")
            return True
        return False

    def generate_share_links(self, url: str, title: str) -> Dict[str, str]:
        """
        生成各平台的分享链接
        
        Args:
            url: 分享的URL
            title: 分享的标题
            
        Returns:
            各平台的分享链接
        """
        encoded_url = url.replace(' ', '%20')
        encoded_title = title.replace(' ', '%20')

        return {
            'twitter': f'https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}',
            'facebook': f'https://www.facebook.com/sharer/sharer.php?u={encoded_url}',
            'linkedin': f'https://www.linkedin.com/shareArticle?mini=true&url={encoded_url}&title={encoded_title}',
            'weibo': f'http://service.weibo.com/share/share.php?url={encoded_url}&title={encoded_title}',
            'wechat': f'https://open.weixin.qq.com/connect/oauth2/authorize?appid=YOUR_APP_ID&redirect_uri={encoded_url}',
        }

    def get_social_stats(self) -> Dict[str, Any]:
        """获取社交媒体统计"""
        return {
            'total_shares': self.social_stats['total_shares'],
            'shares_by_platform': self.social_stats['by_platform'],
            'recent_shares': self.social_stats['recent_shares'][-10:],
            'configured_platforms': [
                platform for platform, creds in self.api_credentials.items()
                if creds.get('api_key') or creds.get('app_id')
            ],
        }

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_auto_share',
                    'type': 'boolean',
                    'label': '启用自动分享',
                },
                {
                    'key': 'auto_share_platforms',
                    'type': 'multiselect',
                    'label': '自动分享平台',
                    'options': [
                        {'value': 'twitter', 'label': 'Twitter'},
                        {'value': 'facebook', 'label': 'Facebook'},
                        {'value': 'linkedin', 'label': 'LinkedIn'},
                    ],
                },
                {
                    'key': 'enable_social_login',
                    'type': 'boolean',
                    'label': '启用社交登录',
                },
                {
                    'key': 'show_social_proof',
                    'type': 'boolean',
                    'label': '显示社交证明',
                },
                {
                    'key': 'instagram_username',
                    'type': 'text',
                    'label': 'Instagram用户名',
                },
                {
                    'key': 'share_button_style',
                    'type': 'select',
                    'label': '分享按钮样式',
                    'options': [
                        {'value': 'default', 'label': '默认'},
                        {'value': 'rounded', 'label': '圆角'},
                        {'value': 'icon-only', 'label': '仅图标'},
                        {'value': 'text', 'label': '文本'},
                    ],
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '测试分享',
                    'action': 'test_share',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = SocialMediaKitPlugin()
