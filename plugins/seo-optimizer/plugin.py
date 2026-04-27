"""
SEO优化插件
提供元标签管理、sitemap生成和SEO分析功能
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from xml.dom import minidom

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from src.api.v1.misc import domain


class SEOOptimizerPlugin(BasePlugin):
    """
    SEO优化插件
    
    功能:
    1. 自动元标签生成
    2. Sitemap XML生成
    3. Robots.txt管理
    4. SEO分析和评分
    5. 规范URL管理
    6. Open Graph标签
    7. Twitter Card支持
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="SEO优化",
            slug="seo-optimizer",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'auto_generate_meta': True,
            'include_images_in_sitemap': True,
            'sitemap_update_frequency': 'daily',
            'canonical_url_base': '',
            'site_name': 'FastBlog',
            'twitter_handle': '',
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章页面元标签
        plugin_hooks.add_filter(
            "page_meta_tags",
            self.generate_article_meta_tags,
            priority=10
        )

        # 首页元标签
        plugin_hooks.add_filter(
            "homepage_meta_tags",
            self.generate_homepage_meta_tags,
            priority=10
        )

        # 生成sitemap
        plugin_hooks.add_action(
            "sitemap_generation",
            self.generate_sitemap,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        # 生成初始sitemap（异步）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建任务
                asyncio.create_task(self.generate_sitemap())
            else:
                # 否则直接运行
                loop.run_until_complete(self.generate_sitemap())
        except Exception as e:
            print(f"[SEOOptimizer] Failed to generate initial sitemap: {e}")

    def generate_article_meta_tags(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成文章页面的元标签
        
        Args:
            meta_data: 页面元数据
            
        Returns:
            增强后的元数据
        """
        if not self.settings.get('auto_generate_meta'):
            return meta_data

        article = meta_data.get('article', {})
        if not article:
            return meta_data

        # 基本元标签
        tags = meta_data.get('tags', [])

        # Title
        title = article.get('title', '')
        tags.append(f'<title>{title} | {self.settings["site_name"]}</title>')

        # Description
        description = article.get('excerpt', '')[:160]
        if description:
            tags.append(f'<meta name="description" content="{description}" />')

        # Keywords
        article_tags = article.get('tags', [])
        if article_tags:
            keywords = ', '.join(article_tags[:10])
            tags.append(f'<meta name="keywords" content="{keywords}" />')

        # Canonical URL
        canonical_url = self._get_canonical_url(article.get('slug', ''))
        if canonical_url:
            tags.append(f'<link rel="canonical" href="{canonical_url}" />')

        # Open Graph标签
        og_tags = self._generate_og_tags(article, 'article')
        tags.extend(og_tags)

        # Twitter Card标签
        twitter_tags = self._generate_twitter_tags(article)
        tags.extend(twitter_tags)

        meta_data['tags'] = tags
        return meta_data

    def generate_homepage_meta_tags(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成首页元标签"""
        if not self.settings.get('auto_generate_meta'):
            return meta_data

        tags = meta_data.get('tags', [])

        # 基本标签
        tags.append(f'<title>{self.settings["site_name"]} - 博客首页</title>')
        tags.append('<meta name="description" content="欢迎访问我们的博客，分享技术文章和见解" />')

        # Canonical
        if self.settings.get('canonical_url_base'):
            tags.append(f'<link rel="canonical" href="{self.settings["canonical_url_base"]}/" />')

        # Open Graph
        tags.append('<meta property="og:type" content="website" />')
        tags.append(f'<meta property="og:title" content="{self.settings["site_name"]}" />')
        tags.append('<meta property="og:description" content="欢迎访问我们的博客" />')

        meta_data['tags'] = tags
        return meta_data

    async def generate_sitemap(self):
        """生成sitemap.xml文件"""
        try:
            # 从数据库获取所有文章和页面
            articles = await self._get_all_articles()
            pages = await self._get_all_pages()

            # 创建XML
            urlset = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

            # 添加首页
            homepage = ET.SubElement(urlset, 'url')
            ET.SubElement(homepage, 'loc').text = self.settings.get('canonical_url_base', 'https://example.com') + '/'
            ET.SubElement(homepage, 'lastmod').text = datetime.now().strftime('%Y-%m-%d')
            ET.SubElement(homepage, 'changefreq').text = 'daily'
            ET.SubElement(homepage, 'priority').text = '1.0'

            # 添加文章
            for article in articles:
                url = ET.SubElement(urlset, 'url')

                loc = self._get_canonical_url(article.get('slug', ''))
                ET.SubElement(url, 'loc').text = loc

                updated_at = article.get('updated_at') or article.get('created_at')
                if updated_at:
                    ET.SubElement(url, 'lastmod').text = updated_at.strftime('%Y-%m-%d')

                ET.SubElement(url, 'changefreq').text = 'weekly'
                ET.SubElement(url, 'priority').text = '0.8'

                # 如果有图片,添加图片信息
                if self.settings.get('include_images_in_sitemap'):
                    images = article.get('images', [])
                    for image in images:
                        image_elem = ET.SubElement(url, 'image:image',
                                                   xmlns='http://www.google.com/schemas/sitemap-image/1.1')
                        ET.SubElement(image_elem, 'image:loc').text = image.get('url', '')
                        if image.get('caption'):
                            ET.SubElement(image_elem, 'image:caption').text = image['caption']

            # 添加页面
            for page in pages:
                url = ET.SubElement(urlset, 'url')
                loc = f"{self.settings.get('canonical_url_base', '')}/page/{page.get('slug', '')}"
                ET.SubElement(url, 'loc').text = loc

                updated_at = page.get('updated_at') or page.get('created_at')
                if updated_at:
                    ET.SubElement(url, 'lastmod').text = updated_at.strftime('%Y-%m-%d')

                ET.SubElement(url, 'changefreq').text = 'monthly'
                ET.SubElement(url, 'priority').text = '0.5'

            # 格式化并保存
            xml_str = minidom.parseString(ET.tostring(urlset, encoding='unicode')).toprettyxml(indent='  ')

            sitemap_path = Path('public/sitemap.xml')
            sitemap_path.parent.mkdir(parents=True, exist_ok=True)

            with open(sitemap_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

            print(f"[SEOOptimizer] Sitemap generated with {len(articles)} articles and {len(pages)} pages")

        except Exception as e:
            print(f"[SEOOptimizer] Failed to generate sitemap: {str(e)}")

    def analyze_seo(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析文章SEO得分
        
        Args:
            article_data: 文章数据
            
        Returns:
            SEO分析报告
        """
        score = 0
        max_score = 100
        issues = []
        suggestions = []
        checks = {}

        # ==================== 标题检查 (15分) ====================
        title = article_data.get('title', '')
        title_check = {
            'name': '标题优化',
            'score': 0,
            'max_score': 15,
            'status': 'error',
            'message': ''
        }

        if len(title) >= 30 and len(title) <= 60:
            title_check['score'] = 15
            title_check['status'] = 'success'
            title_check['message'] = f'标题长度{len(title)}字符，符合要求'
            score += 15
        elif len(title) > 0:
            title_check['score'] = 8
            title_check['status'] = 'warning'
            title_check['message'] = f'标题长度{len(title)}字符，建议在30-60个字符之间'
            score += 8
            suggestions.append({
                'type': 'title_length',
                'priority': 'medium',
                'message': '标题长度建议在30-60个字符之间，当前:' + str(len(title))
            })
        else:
            title_check['message'] = '缺少标题'
            issues.append({
                'type': 'missing_title',
                'priority': 'high',
                'message': '文章必须设置标题'
            })
        checks['title'] = title_check

        # ==================== 描述检查 (15分) ====================
        excerpt = article_data.get('excerpt', '')
        desc_check = {
            'name': 'Meta描述',
            'score': 0,
            'max_score': 15,
            'status': 'error',
            'message': ''
        }

        if len(excerpt) >= 120 and len(excerpt) <= 160:
            desc_check['score'] = 15
            desc_check['status'] = 'success'
            desc_check['message'] = f'描述长度{len(excerpt)}字符，完美'
            score += 15
        elif len(excerpt) > 0:
            desc_check['score'] = 8
            desc_check['status'] = 'warning'
            desc_check['message'] = f'描述长度{len(excerpt)}字符，建议120-160字符'
            score += 8
            suggestions.append({
                'type': 'description_length',
                'priority': 'medium',
                'message': f'Meta描述建议120-160字符，当前:{len(excerpt)}'
            })
        else:
            desc_check['message'] = '缺少摘要描述'
            issues.append({
                'type': 'missing_description',
                'priority': 'high',
                'message': '建议添加120-160字符的摘要描述'
            })
            suggestions.append({
                'type': 'add_description',
                'priority': 'high',
                'message': '添加Meta描述可以提高点击率'
            })
        checks['description'] = desc_check

        # ==================== 关键词检查 (10分) ====================
        tags = article_data.get('tags', [])
        keyword_check = {
            'name': '关键词/标签',
            'score': 0,
            'max_score': 10,
            'status': 'error',
            'message': ''
        }

        if len(tags) >= 5:
            keyword_check['score'] = 10
            keyword_check['status'] = 'success'
            keyword_check['message'] = f'已添加{len(tags)}个标签，很好'
            score += 10
        elif len(tags) >= 3:
            keyword_check['score'] = 8
            keyword_check['status'] = 'warning'
            keyword_check['message'] = f'已添加{len(tags)}个标签，建议至少5个'
            score += 8
        elif len(tags) > 0:
            keyword_check['score'] = 4
            keyword_check['status'] = 'warning'
            keyword_check['message'] = f'仅{len(tags)}个标签，建议添加更多'
            score += 4
            suggestions.append({
                'type': 'more_tags',
                'priority': 'low',
                'message': f'建议添加至少5个相关标签，当前:{len(tags)}'
            })
        else:
            keyword_check['message'] = '未添加标签'
            suggestions.append({
                'type': 'add_tags',
                'priority': 'medium',
                'message': '添加相关标签有助于SEO和分类'
            })
        checks['keywords'] = keyword_check

        # ==================== 内容长度检查 (20分) ====================
        content = article_data.get('content', '')
        word_count = len(content.split())
        content_check = {
            'name': '内容长度',
            'score': 0,
            'max_score': 20,
            'status': 'error',
            'message': '',
            'word_count': word_count
        }

        if word_count >= 1500:
            content_check['score'] = 20
            content_check['status'] = 'success'
            content_check['message'] = f'内容{word_count}字，非常充实'
            score += 20
        elif word_count >= 1000:
            content_check['score'] = 18
            content_check['status'] = 'success'
            content_check['message'] = f'内容{word_count}字，很好'
            score += 18
        elif word_count >= 500:
            content_check['score'] = 15
            content_check['status'] = 'warning'
            content_check['message'] = f'内容{word_count}字，建议增加到1000字以上'
            score += 15
            suggestions.append({
                'type': 'content_length',
                'priority': 'medium',
                'message': f'文章内容建议1000字以上，当前:{word_count}'
            })
        elif word_count >= 300:
            content_check['score'] = 10
            content_check['status'] = 'warning'
            content_check['message'] = f'内容{word_count}字，偏短'
            score += 10
            suggestions.append({
                'type': 'content_too_short',
                'priority': 'high',
                'message': '文章内容建议至少500字，以提高SEO排名'
            })
        else:
            content_check['message'] = f'内容仅{word_count}字，太短'
            suggestions.append({
                'type': 'content_very_short',
                'priority': 'high',
                'message': '文章内容过短，建议扩充到500字以上'
            })
        checks['content'] = content_check

        # ==================== 图片检查 (10分) ====================
        images = article_data.get('images', [])
        image_check = {
            'name': '图片优化',
            'score': 0,
            'max_score': 10,
            'status': 'error',
            'message': '',
            'total_images': len(images),
            'images_without_alt': 0
        }

        if images:
            # 检查alt文本
            images_without_alt = [img for img in images if not img.get('alt')]
            image_check['images_without_alt'] = len(images_without_alt)

            if len(images_without_alt) == 0:
                image_check['score'] = 10
                image_check['status'] = 'success'
                image_check['message'] = f'{len(images)}张图片都有alt文本，完美'
                score += 10
            else:
                image_check['score'] = 5
                image_check['status'] = 'warning'
                image_check['message'] = f'{len(images_without_alt)}/{len(images)}张图片缺少alt文本'
                score += 5
                suggestions.append({
                    'type': 'missing_alt',
                    'priority': 'medium',
                    'message': f'{len(images_without_alt)}张图片缺少alt文本，影响无障碍访问和SEO'
                })
        else:
            image_check['message'] = '未添加图片'
            suggestions.append({
                'type': 'add_images',
                'priority': 'low',
                'message': '添加图片可以提高用户体验和停留时间'
            })
        checks['images'] = image_check

        # ==================== 内部链接检查 (10分) ====================
        internal_links = self._count_internal_links(content)
        link_check = {
            'name': '内部链接',
            'score': 0,
            'max_score': 10,
            'status': 'error',
            'message': '',
            'count': internal_links
        }

        if internal_links >= 3:
            link_check['score'] = 10
            link_check['status'] = 'success'
            link_check['message'] = f'{internal_links}个内部链接，很好'
            score += 10
        elif internal_links >= 2:
            link_check['score'] = 8
            link_check['status'] = 'success'
            link_check['message'] = f'{internal_links}个内部链接'
            score += 8
        elif internal_links == 1:
            link_check['score'] = 5
            link_check['status'] = 'warning'
            link_check['message'] = '仅1个内部链接'
            score += 5
            suggestions.append({
                'type': 'more_internal_links',
                'priority': 'low',
                'message': '建议添加2-3个内部链接，提高页面关联性'
            })
        else:
            link_check['message'] = '没有内部链接'
            suggestions.append({
                'type': 'add_internal_links',
                'priority': 'medium',
                'message': '添加内部链接有助于SEO和用户体验'
            })
        checks['internal_links'] = link_check

        # ==================== URL结构检查 (10分) ====================
        slug = article_data.get('slug', '')
        url_check = {
            'name': 'URL结构',
            'score': 0,
            'max_score': 10,
            'status': 'error',
            'message': ''
        }

        if slug and len(slug) < 100 and '-' in slug and slug.isascii():
            url_check['score'] = 10
            url_check['status'] = 'success'
            url_check['message'] = 'URL结构良好'
            score += 10
        elif slug:
            url_check['score'] = 5
            url_check['status'] = 'warning'
            url_check['message'] = 'URL可以优化'
            score += 5
            if len(slug) >= 100:
                suggestions.append({
                    'type': 'url_too_long',
                    'priority': 'low',
                    'message': 'URL过长，建议缩短到100字符以内'
                })
            if '-' not in slug:
                suggestions.append({
                    'type': 'url_no_hyphen',
                    'priority': 'low',
                    'message': 'URL应使用连字符(-)分隔单词'
                })
        else:
            url_check['message'] = 'URL slug未设置'
            issues.append({
                'type': 'missing_slug',
                'priority': 'high',
                'message': '请设置URL slug'
            })
        checks['url'] = url_check

        # ==================== 移动端友好检查 (5分) ====================
        mobile_check = {
            'name': '移动端友好',
            'score': 5,
            'max_score': 5,
            'status': 'success',
            'message': '主题支持响应式设计'
        }
        score += 5
        checks['mobile'] = mobile_check

        # ==================== 计算总分和等级 ====================
        percentage = round((score / max_score) * 100)

        if percentage >= 90:
            grade = 'A'
            grade_color = 'green'
        elif percentage >= 80:
            grade = 'B'
            grade_color = 'blue'
        elif percentage >= 70:
            grade = 'C'
            grade_color = 'yellow'
        elif percentage >= 60:
            grade = 'D'
            grade_color = 'orange'
        else:
            grade = 'F'
            grade_color = 'red'

        return {
            'overall': {
                'score': score,
                'max_score': max_score,
                'percentage': percentage,
                'grade': grade,
                'grade_color': grade_color
            },
            'checks': checks,
            'issues': issues,
            'suggestions': suggestions,
            'summary': {
                'total_issues': len(issues),
                'total_suggestions': len(suggestions),
                'high_priority': len([i for i in issues if i.get('priority') == 'high']),
                'passed_checks': len([c for c in checks.values() if c['status'] == 'success'])
            }
        }

    def generate_robots_txt(self) -> str:
        """生成robots.txt内容"""
        robots = """# robots.txt
User-agent: *
Allow: /

# Sitemap
Sitemap: {}/sitemap.xml

# Disallow admin areas
Disallow: /admin/
Disallow: /api/
Disallow: /login
""".format(self.settings.get('canonical_url_base', 'https://example.com'))

        return robots

    def _get_canonical_url(self, slug: str) -> str:
        """获取规范URL"""
        base = self.settings.get('canonical_url_base', '').rstrip('/')
        return f"{base}/p/{slug}" if base and slug else ''

    def _generate_og_tags(self, article: Dict[str, Any], content_type: str) -> List[str]:
        """生成Open Graph标签"""
        tags = []

        tags.append('<meta property="og:type" content="article" />')
        tags.append(f'<meta property="og:title" content="{article.get("title", "")}" />')

        excerpt = article.get('excerpt', '')[:200]
        if excerpt:
            tags.append(f'<meta property="og:description" content="{excerpt}" />')

        # 封面图片
        featured_image = article.get('featured_image')
        if featured_image:
            tags.append(f'<meta property="og:image" content="{featured_image}" />')

        # URL
        canonical_url = self._get_canonical_url(article.get('slug', ''))
        if canonical_url:
            tags.append(f'<meta property="og:url" content="{canonical_url}" />')

        # Site name
        tags.append(f'<meta property="og:site_name" content="{self.settings["site_name"]}" />')

        return tags

    def _generate_twitter_tags(self, article: Dict[str, Any]) -> List[str]:
        """生成Twitter Card标签"""
        tags = []

        tags.append('<meta name="twitter:card" content="summary_large_image" />')

        if self.settings.get('twitter_handle'):
            tags.append(f'<meta name="twitter:site" content="@{self.settings["twitter_handle"]}" />')

        tags.append(f'<meta name="twitter:title" content="{article.get("title", "")}" />')

        excerpt = article.get('excerpt', '')[:200]
        if excerpt:
            tags.append(f'<meta name="twitter:description" content="{excerpt}" />')

        featured_image = article.get('featured_image')
        if featured_image:
            tags.append(f'<meta name="twitter:image" content="{featured_image}" />')

        return tags

    async def _get_all_articles(self) -> List[Dict[str, Any]]:
        """从公开API获取所有已发布文章"""
        try:
            from shared.services.plugin_manager import plugin_api

            # 使用公开API获取文章，避免直接操作数据库
            articles = await plugin_api.get_published_articles(
                limit=1000,  # 获取最多1000篇文章
                offset=0,
                include_hidden=False
            )

            print(f"[SEOOptimizer] Loaded {len(articles)} published articles via public API")
            return articles

        except Exception as e:
            print(f"[SEOOptimizer] Failed to get articles via public API: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_all_pages(self) -> List[Dict[str, Any]]:
        """从公开API获取所有页面"""
        try:
            from shared.services.plugin_manager import plugin_api

            # 使用公开API获取页面，避免直接操作数据库
            pages = await plugin_api.get_all_pages(include_draft=False)

            print(f"[SEOOptimizer] Loaded {len(pages)} published pages via public API")
            return pages

        except Exception as e:
            print(f"[SEOOptimizer] Failed to get pages via public API: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _count_internal_links(self, content: str) -> int:
        """计算内部链接数量"""
        import re
        # 简单匹配相对URL或本站域名
        pattern = r'href=["\'](/|https?://example\.com)'
        return len(re.findall(pattern, content))

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'auto_generate_meta',
                    'type': 'boolean',
                    'label': '自动生成元标签',
                    'help': '自动为页面生成SEO元标签',
                },
                {
                    'key': 'site_name',
                    'type': 'text',
                    'label': '网站名称',
                    'placeholder': 'FastBlog',
                },
                {
                    'key': 'canonical_url_base',
                    'type': 'text',
                    'label': '规范URL基础',
                    'placeholder': domain,
                    'help': '用于生成规范URL的基础地址',
                },
                {
                    'key': 'twitter_handle',
                    'type': 'text',
                    'label': 'Twitter账号',
                    'placeholder': 'username',
                    'help': '不含@符号',
                },
                {
                    'key': 'include_images_in_sitemap',
                    'type': 'boolean',
                    'label': 'Sitemap包含图片',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '重新生成Sitemap',
                    'action': 'generate_sitemap',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '下载robots.txt',
                    'action': 'download_robots_txt',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = SEOOptimizerPlugin()
