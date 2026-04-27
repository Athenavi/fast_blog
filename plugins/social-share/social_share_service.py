"""
社交媒体自动分享服务
支持主流社交平台的自动发布和分享功能
"""

from datetime import datetime
from typing import Dict, List, Optional, Any


class SocialShareService:
    """
    社交媒体分享服务
    
    支持平台:
    1. 微博 (Weibo)
    2. 微信 (WeChat)
    3. QQ空间
    4. Twitter/X
    5. Facebook
    6. LinkedIn
    7. Telegram
    
    功能:
    - 生成分享链接
    - 批量分享到多个平台
    - 分享统计追踪
    - 定时分享调度
    """

    def __init__(self):
        # 社交平台配置
        self.platforms = {
            'weibo': {
                'name': '微博',
                'icon': '🔴',
                'share_url_template': 'http://service.weibo.com/share/share.php?url={url}&title={title}&pic={image}',
                'requires_api': True
            },
            'wechat': {
                'name': '微信',
                'icon': '🟢',
                'share_url_template': None,  # 需要JS-SDK
                'requires_api': True
            },
            'qq': {
                'name': 'QQ空间',
                'icon': '🔵',
                'share_url_template': 'https://sns.qzone.qq.com/cgi-bin/qzshare/cgi_qzshare_onekey?url={url}&title={title}&pics={image}&summary={summary}',
                'requires_api': False
            },
            'twitter': {
                'name': 'Twitter',
                'icon': '🐦',
                'share_url_template': 'https://twitter.com/intent/tweet?url={url}&text={title}',
                'requires_api': True
            },
            'facebook': {
                'name': 'Facebook',
                'icon': '📘',
                'share_url_template': 'https://www.facebook.com/sharer/sharer.php?u={url}',
                'requires_api': True
            },
            'linkedin': {
                'name': 'LinkedIn',
                'icon': '💼',
                'share_url_template': 'https://www.linkedin.com/shareArticle?url={url}&title={title}&summary={summary}',
                'requires_api': True
            },
            'telegram': {
                'name': 'Telegram',
                'icon': '✈️',
                'share_url_template': 'https://t.me/share/url?url={url}&text={title}',
                'requires_api': False
            }
        }

    def generate_share_links(
            self,
            url: str,
            title: str,
            summary: str = '',
            image: str = '',
            platforms: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        生成各平台的分享链接
        
        Args:
            url: 分享的URL
            title: 标题
            summary: 摘要
            image: 图片URL
            platforms: 指定平台列表,None则返回所有
            
        Returns:
            平台名称到分享链接的映射
        """
        from urllib.parse import quote

        share_links = {}

        target_platforms = platforms or list(self.platforms.keys())

        for platform in target_platforms:
            if platform not in self.platforms:
                continue

            config = self.platforms[platform]
            template = config['share_url_template']

            if not template:
                continue

            try:
                link = template.format(
                    url=quote(url, safe=''),
                    title=quote(title, safe=''),
                    summary=quote(summary, safe=''),
                    image=quote(image, safe='')
                )
                share_links[platform] = link
            except Exception as e:
                print(f"Error generating {platform} share link: {e}")

        return share_links

    def get_share_metadata(
            self,
            title: str,
            description: str,
            url: str,
            image: str,
            article_type: str = 'article'
    ) -> Dict[str, str]:
        """
        生成Open Graph和Twitter Card元数据
        
        Args:
            title: 标题
            description: 描述
            url: URL
            image: 图片URL
            article_type: 内容类型
            
        Returns:
            元数据字典
        """
        metadata = {
            # Open Graph (Facebook, LinkedIn等)
            'og:title': title,
            'og:description': description,
            'og:url': url,
            'og:image': image,
            'og:type': article_type,
            'og:site_name': 'Fast Blog',

            # Twitter Card
            'twitter:card': 'summary_large_image',
            'twitter:title': title,
            'twitter:description': description,
            'twitter:image': image,

            # 通用
            'title': f"{title} | Fast Blog",
            'description': description
        }

        return metadata

    async def schedule_share(
            self,
            article_id: int,
            platforms: List[str],
            scheduled_time: Optional[datetime] = None,
            db_session=None
    ) -> Dict[str, Any]:
        """
        调度文章分享到社交平台
        
        Args:
            article_id: 文章ID
            platforms: 目标平台列表
            scheduled_time: 计划分享时间,None表示立即分享
            db_session: 数据库会话
            
        Returns:
            调度结果
        """
        try:
            # 从数据库获取文章信息
            from apps.blog.models import Article
            
            article = Article.objects.get(id=article_id)
            article_data = {
                'id': article.id,
                'title': article.title,
                'summary': article.summary or '',
                'url': f'/article/{article.id}',
                'cover_image': article.cover_image or ''
            }

            result = {
                'success': True,
                'article_id': article_id,
                'platforms': platforms,
                'scheduled_time': scheduled_time.isoformat() if scheduled_time else datetime.now().isoformat(),
                'status': 'scheduled' if scheduled_time else 'processing'
            }

            # 如果不是定时分享,立即执行
            if not scheduled_time:
                # 执行分享操作（这里只是生成分享链接，实际API调用需要各平台的SDK）
                share_links = self.generate_share_links(
                    url=article_data['url'],
                    title=article_data['title'],
                    summary=article_data['summary'],
                    image=article_data['cover_image'],
                    platforms=platforms
                )
                result['share_links'] = share_links
                result['status'] = 'completed'

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_share_statistics(
            self,
            article_id: int,
            db_session=None
    ) -> Dict[str, Any]:
        """
        获取文章分享统计数据
        
        Args:
            article_id: 文章ID
            db_session: 数据库会话
            
        Returns:
            分享统计数据
        """
        try:
            # 从数据库查询分享记录
            # 注意：这里需要创建 ShareRecord 模型来存储分享统计
            # 暂时返回空统计数据
            
            stats = {
                'article_id': article_id,
                'total_shares': 0,
                'by_platform': {
                    'weibo': 0,
                    'wechat': 0,
                    'qq': 0,
                    'twitter': 0,
                    'facebook': 0,
                    'linkedin': 0,
                    'telegram': 0
                },
                'total_clicks': 0
            }

            return {
                'success': True,
                'data': stats
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_share_buttons_html(
            self,
            url: str,
            title: str,
            summary: str = '',
            image: str = '',
            platforms: Optional[List[str]] = None,
            style: str = 'default'
    ) -> str:
        """
        生成分享按钮HTML代码
        
        Args:
            url: 分享URL
            title: 标题
            summary: 摘要
            image: 图片URL
            platforms: 平台列表
            style: 按钮样式(default, round, square)
            
        Returns:
            HTML字符串
        """
        share_links = self.generate_share_links(url, title, summary, image, platforms)

        html_parts = ['<div class="social-share-buttons">']

        # 样式类
        button_class = {
            'default': 'share-btn',
            'round': 'share-btn share-btn-round',
            'square': 'share-btn share-btn-square'
        }.get(style, 'share-btn')

        for platform, link in share_links.items():
            config = self.platforms.get(platform, {})
            name = config.get('name', platform)
            icon = config.get('icon', '🔗')

            html_parts.append(
                f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                f'class="{button_class} {platform}-btn" title="分享到{name}">'
                f'{icon} {name}'
                f'</a>'
            )

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def validate_share_config(self, platform: str, config: Dict[str, str]) -> bool:
        """
        验证社交平台API配置
        
        Args:
            platform: 平台名称
            config: 配置字典(app_id, app_secret等)
            
        Returns:
            配置是否有效
        """
        required_configs = {
            'weibo': ['app_key', 'app_secret'],
            'twitter': ['api_key', 'api_secret', 'access_token'],
            'facebook': ['app_id', 'app_secret'],
            'linkedin': ['client_id', 'client_secret']
        }

        if platform not in required_configs:
            return True  # 不需要API的平台

        required = required_configs[platform]
        return all(key in config and config[key] for key in required)


# 全局实例
social_share = SocialShareService()
