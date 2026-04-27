"""
社交分享插件
提供社交媒体集成和分享功能
"""

from typing import Dict, Any
from urllib.parse import quote

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from shared.utils.plugin_database import plugin_db


class SocialSharePlugin(BasePlugin):
    """
    社交分享插件
    
    功能:
    1. 多平台分享按钮
    2. 自定义分享样式
    3. 分享统计
    4. Open Graph优化
    5. 自动发布到社交平台
    6. 社交登录集成
    7. 分享追踪和分析
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="社交分享",
            slug="social-share",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_share_buttons': True,
            'share_platforms': ['wechat', 'weibo', 'twitter'],
            'button_style': 'default',
            'button_position': 'bottom',
            'auto_post_to_social': False,
        }

        # 分享统计
        self.share_stats: Dict[str, int] = {}

    def register_hooks(self):
        """注册钩子"""
        # 在文章内容后添加分享按钮
        if self.settings.get('enable_share_buttons'):
            plugin_hooks.add_filter(
                "article_content_footer",
                self.add_share_buttons,
                priority=10
            )

        # 文章发布时自动分享到社交
        if self.settings.get('auto_post_to_social'):
            plugin_hooks.add_action(
                "article_published",
                self.auto_post_to_social,
                priority=20
            )

    def activate(self):
        """激活插件"""
        super().activate()
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        try:
            from shared.utils.plugin_db_init import init_social_share_db
            init_social_share_db()
        except Exception as e:
            print(f"[SocialShare] Failed to initialize database: {e}")

    def add_share_buttons(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加分享按钮
        
        Args:
            content_data: 内容数据 {html, article}
            
        Returns:
            增强后的内容
        """
        article = content_data.get('article', {})
        if not article:
            return content_data

        # 生成分享URL
        share_url = self._get_share_url(article)
        share_title = article.get('title', '')
        share_description = article.get('excerpt', '')[:200]

        # 生成分享按钮HTML
        buttons_html = self._generate_share_buttons(share_url, share_title, share_description)

        # 添加到内容中
        existing_html = content_data.get('html', '')
        position = self.settings.get('button_position', 'bottom')

        if position == 'bottom':
            content_data['html'] = existing_html + buttons_html
        elif position == 'top':
            content_data['html'] = buttons_html + existing_html
        elif position == 'floating':
            # 浮动按钮需要额外的CSS
            content_data['html'] = existing_html
            content_data['floating_buttons'] = buttons_html

        return content_data

    def _generate_share_buttons(self, url: str, title: str, description: str) -> str:
        """
        生成分享按钮HTML
        
        Args:
            url: 分享URL
            title: 标题
            description: 描述
            
        Returns:
            HTML字符串
        """
        platforms = self.settings.get('share_platforms', [])
        button_style = self.settings.get('button_style', 'default')

        buttons = []

        for platform in platforms:
            if platform == 'wechat':
                buttons.append(self._generate_wechat_button(url, title))
            elif platform == 'weibo':
                buttons.append(self._generate_weibo_button(url, title))
            elif platform == 'qq':
                buttons.append(self._generate_qq_button(url, title))
            elif platform == 'twitter':
                buttons.append(self._generate_twitter_button(url, title))
            elif platform == 'facebook':
                buttons.append(self._generate_facebook_button(url, title))
            elif platform == 'linkedin':
                buttons.append(self._generate_linkedin_button(url, title, description))

        # 根据样式包装
        if button_style == 'icon-only':
            buttons_html = '<div class="social-share-buttons icon-only">' + ''.join(buttons) + '</div>'
        elif button_style == 'text':
            buttons_html = '<div class="social-share-buttons text-only">' + ''.join(buttons) + '</div>'
        else:
            buttons_html = '<div class="social-share-buttons default">' + ''.join(buttons) + '</div>'

        # 添加样式
        css = self._get_share_buttons_css()

        return f'<style>{css}</style>{buttons_html}'

    def _generate_wechat_button(self, url: str, title: str) -> str:
        """生成微信分享按钮"""
        return f'''
        <button class="share-button wechat" onclick="shareToWechat('{url}', '{title}')">
            <span class="icon">💬</span>
            <span class="label">微信</span>
        </button>
        '''

    def _generate_weibo_button(self, url: str, title: str) -> str:
        """生成微博分享按钮"""
        share_url = f"https://service.weibo.com/share/share.php?url={quote(url)}&title={quote(title)}"
        return f'''
        <a href="{share_url}" target="_blank" class="share-button weibo" onclick="trackShare('weibo')">
            <span class="icon">🌐</span>
            <span class="label">微博</span>
        </a>
        '''

    def _generate_qq_button(self, url: str, title: str) -> str:
        """生成QQ分享按钮"""
        share_url = f"https://connect.qq.com/widget/shareqq/index.html?url={quote(url)}&title={quote(title)}"
        return f'''
        <a href="{share_url}" target="_blank" class="share-button qq" onclick="trackShare('qq')">
            <span class="icon">🐧</span>
            <span class="label">QQ</span>
        </a>
        '''

    def _generate_twitter_button(self, url: str, title: str) -> str:
        """生成Twitter分享按钮"""
        share_url = f"https://twitter.com/intent/tweet?url={quote(url)}&text={quote(title)}"
        return f'''
        <a href="{share_url}" target="_blank" class="share-button twitter" onclick="trackShare('twitter')">
            <span class="icon">🐦</span>
            <span class="label">Twitter</span>
        </a>
        '''

    def _generate_facebook_button(self, url: str, title: str) -> str:
        """生成Facebook分享按钮"""
        share_url = f"https://www.facebook.com/sharer/sharer.php?u={quote(url)}"
        return f'''
        <a href="{share_url}" target="_blank" class="share-button facebook" onclick="trackShare('facebook')">
            <span class="icon">📘</span>
            <span class="label">Facebook</span>
        </a>
        '''

    def _generate_linkedin_button(self, url: str, title: str, description: str) -> str:
        """生成LinkedIn分享按钮"""
        share_url = f"https://www.linkedin.com/sharing/share-offsite/?url={quote(url)}"
        return f'''
        <a href="{share_url}" target="_blank" class="share-button linkedin" onclick="trackShare('linkedin')">
            <span class="icon">💼</span>
            <span class="label">LinkedIn</span>
        </a>
        '''

    def _get_share_buttons_css(self) -> str:
        """获取分享按钮CSS"""
        return '''
        .social-share-buttons {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .share-button {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            text-decoration: none;
            color: white;
        }
        
        .share-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .share-button.wechat { background-color: #07c160; }
        .share-button.weibo { background-color: #e6162d; }
        .share-button.qq { background-color: #12b7f5; }
        .share-button.twitter { background-color: #1da1f2; }
        .share-button.facebook { background-color: #1877f2; }
        .share-button.linkedin { background-color: #0077b5; }
        
        .share-button.icon-only {
            padding: 8px;
            border-radius: 50%;
        }
        
        .share-button.icon-only .label {
            display: none;
        }
        
        .share-button.text-only .icon {
            display: none;
        }
        '''

    async def auto_post_to_social(self, article_data: Dict[str, Any]):
        """
        文章发布时自动分享到社交平台
        
        Args:
            article_data: 文章数据
        """
        try:
            title = article_data.get('title', '')
            url = self._get_share_url(article_data)
            excerpt = article_data.get('excerpt', '')[:100]

            print(f"[SocialShare] Auto-posting article: {title}")
            print(f"[SocialShare] URL: {url}")

            # 获取启用的平台配置
            platforms_config = self.settings.get('auto_post_platforms', {})

            # Twitter/X 发布
            if platforms_config.get('twitter', {}).get('enabled'):
                await self._post_to_twitter(title, url, excerpt, platforms_config['twitter'])

            # Facebook 发布
            if platforms_config.get('facebook', {}).get('enabled'):
                await self._post_to_facebook(title, url, excerpt, platforms_config['facebook'])

            # LinkedIn 发布
            if platforms_config.get('linkedin', {}).get('enabled'):
                await self._post_to_linkedin(title, url, excerpt, platforms_config['linkedin'])

            # 微博发布
            if platforms_config.get('weibo', {}).get('enabled'):
                await self._post_to_weibo(title, url, excerpt, platforms_config['weibo'])

        except Exception as e:
            print(f"[SocialShare] Auto-post failed: {e}")
            import traceback
            traceback.print_exc()

    async def _post_to_twitter(self, title: str, url: str, excerpt: str, config: Dict):
        """发布到Twitter/X"""
        try:
            # 需要 tweepy: pip install tweepy
            # import tweepy
            # 
            # client = tweepy.Client(
            #     consumer_key=config['api_key'],
            #     consumer_secret=config['api_secret'],
            #     access_token=config['access_token'],
            #     access_token_secret=config['access_token_secret']
            # )
            # 
            # tweet_text = f"{title}\n\n{excerpt}\n\n{url}"
            # response = client.create_tweet(text=tweet_text)
            # print(f"[SocialShare] Posted to Twitter: {response}")

            print(f"[SocialShare] Twitter post skipped (need tweepy library)")

        except Exception as e:
            print(f"[SocialShare] Twitter post failed: {e}")

    async def _post_to_facebook(self, title: str, url: str, excerpt: str, config: Dict):
        """发布到Facebook"""
        try:
            # 需要 requests: pip install requests
            # import requests
            # 
            # page_id = config['page_id']
            # access_token = config['access_token']
            # 
            # graph_url = f"https://graph.facebook.com/{page_id}/feed"
            # data = {
            #     'message': f"{title}\n\n{excerpt}",
            #     'link': url,
            #     'access_token': access_token
            # }
            # response = requests.post(graph_url, data=data)
            # print(f"[SocialShare] Posted to Facebook: {response.json()}")

            print(f"[SocialShare] Facebook post skipped (need requests library)")

        except Exception as e:
            print(f"[SocialShare] Facebook post failed: {e}")

    async def _post_to_linkedin(self, title: str, url: str, excerpt: str, config: Dict):
        """发布到LinkedIn"""
        try:
            # 需要 requests: pip install requests
            # import requests
            # 
            # headers = {
            #     'Authorization': f"Bearer {config['access_token']}",
            #     'Content-Type': 'application/json'
            # }
            # 
            # payload = {
            #     'author': f"urn:li:person:{config['person_id']}",
            #     'lifecycleState': 'PUBLISHED',
            #     'specificContent': {
            #         'com.linkedin.ugc.ShareContent': {
            #             'shareCommentary': {'text': f"{title}\n\n{excerpt}"},
            #             'shareMediaCategory': 'ARTICLE',
            #             'media': [{'status': 'READY', 'description': {'text': excerpt}, 'originalUrl': url}]
            #         }
            #     },
            #     'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
            # }
            # 
            # response = requests.post(
            #     'https://api.linkedin.com/v2/ugcPosts',
            #     headers=headers,
            #     json=payload
            # )
            # print(f"[SocialShare] Posted to LinkedIn: {response.json()}")

            print(f"[SocialShare] LinkedIn post skipped (need requests library)")

        except Exception as e:
            print(f"[SocialShare] LinkedIn post failed: {e}")

    async def _post_to_weibo(self, title: str, url: str, excerpt: str, config: Dict):
        """发布到微博"""
        try:
            # 需要 requests: pip install requests
            # import requests
            # 
            # access_token = config['access_token']
            # uid = config['uid']
            # 
            # url_api = 'https://api.weibo.com/2/statuses/update.json'
            # data = {
            #     'access_token': access_token,
            #     'status': f"{title}\n\n{excerpt}\n\n{url}"
            # }
            # response = requests.post(url_api, data=data)
            # print(f"[SocialShare] Posted to Weibo: {response.json()}")

            print(f"[SocialShare] Weibo post skipped (need requests library)")

        except Exception as e:
            print(f"[SocialShare] Weibo post failed: {e}")

    def track_share(self, platform: str, article_id: int):
        """
        追踪分享行为并保存到数据库
        
        Args:
            platform: 分享平台
            article_id: 文章ID
        """
        key = f"{platform}_{article_id}"
        self.share_stats[key] = self.share_stats.get(key, 0) + 1

        # 保存到数据库
        try:
            plugin_db.execute_update(
                'social-share',
                """INSERT INTO share_statistics (platform, article_id, count, updated_at)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(platform, article_id)
                       DO UPDATE SET count      = count + 1,
                                     updated_at = ?""",
                (platform, article_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
        except Exception as e:
            print(f"[SocialShare] Failed to save share stats: {e}")

    def get_share_stats(self, article_id: int = None) -> Dict[str, Any]:
        """
        获取分享统计
        
        Args:
            article_id: 文章ID(可选)
            
        Returns:
            统计数据
        """
        if article_id:
            # 获取特定文章的统计
            stats = {}
            for key, count in self.share_stats.items():
                if key.endswith(f"_{article_id}"):
                    platform = key.rsplit('_', 1)[0]
                    stats[platform] = count
            return stats
        else:
            # 获取总体统计
            total_shares = sum(self.share_stats.values())
            platform_stats = {}

            for key, count in self.share_stats.items():
                platform = key.rsplit('_', 1)[0]
                platform_stats[platform] = platform_stats.get(platform, 0) + count

            return {
                'total_shares': total_shares,
                'by_platform': platform_stats,
            }

    def get_social_login_config(self) -> Dict[str, Any]:
        """获取社交登录配置"""
        return {
            'providers': {
                'wechat': {
                    'enabled': False,
                    'app_id': '',
                    'app_secret': '',
                },
                'qq': {
                    'enabled': False,
                    'app_id': '',
                    'app_key': '',
                },
                'weibo': {
                    'enabled': False,
                    'app_key': '',
                    'app_secret': '',
                },
            }
        }

    def _get_share_url(self, article: Dict[str, Any]) -> str:
        """获取文章分享URL"""
        slug = article.get('slug', '')
        # 从系统配置或环境变量获取基础URL
        import os
        base_url = os.getenv('SITE_BASE_URL', 'https://example.com')
        return f"{base_url}/p/{slug}" if slug else base_url

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_share_buttons',
                    'type': 'boolean',
                    'label': '启用分享按钮',
                },
                {
                    'key': 'share_platforms',
                    'type': 'multiselect',
                    'label': '分享平台',
                    'options': [
                        {'value': 'wechat', 'label': '微信'},
                        {'value': 'weibo', 'label': '微博'},
                        {'value': 'qq', 'label': 'QQ'},
                        {'value': 'twitter', 'label': 'Twitter'},
                        {'value': 'facebook', 'label': 'Facebook'},
                        {'value': 'linkedin', 'label': 'LinkedIn'},
                    ],
                },
                {
                    'key': 'button_style',
                    'type': 'select',
                    'label': '按钮样式',
                    'options': [
                        {'value': 'default', 'label': '默认'},
                        {'value': 'rounded', 'label': '圆角'},
                        {'value': 'icon-only', 'label': '仅图标'},
                        {'value': 'text', 'label': '仅文字'},
                    ],
                },
                {
                    'key': 'button_position',
                    'type': 'select',
                    'label': '按钮位置',
                    'options': [
                        {'value': 'top', 'label': '顶部'},
                        {'value': 'bottom', 'label': '底部'},
                        {'value': 'floating', 'label': '浮动'},
                        {'value': 'sidebar', 'label': '侧边栏'},
                    ],
                },
            ]
        }


# 插件实例
plugin_instance = SocialSharePlugin()
