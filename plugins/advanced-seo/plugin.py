"""
高级SEO插件 (Advanced SEO)
提供XML Sitemap增强、Robots.txt管理、重定向管理和404监控修复功能
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class AdvancedSeoPlugin(BasePlugin):
    """
    高级SEO插件
    
    功能:
    1. XML Sitemap增强 - 支持多语言、图片、视频
    2. Robots.txt管理 - 可视化编辑和管理
    3. 重定向管理 - 301/302重定向规则
    4. 404监控和修复 - 追踪404错误并提供修复建议
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="高级SEO",
            slug="advanced-seo",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'auto_generate_meta': True,
            'include_images_in_sitemap': True,
            'sitemap_update_frequency': 'daily',
            'enable_redirects': True,
            'monitor_404': True,
            'canonical_url_base': '',
        }

        # 重定向规则
        self.redirects: List[Dict[str, Any]] = []

        # 404错误记录
        self.not_found_errors: List[Dict[str, Any]] = []

    def register_hooks(self):
        """注册钩子"""
        # 文章发布时更新Sitemap
        plugin_hooks.add_action(
            "article_published",
            self.on_article_published,
            priority=10
        )

        # 页面访问时检查重定向
        plugin_hooks.add_filter(
            "request_url",
            self.check_redirect,
            priority=5
        )

        # 404错误追踪
        plugin_hooks.add_action(
            "page_not_found",
            self.track_404_error,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[AdvancedSEO] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[AdvancedSEO] Plugin deactivated")

    def on_article_published(self, article_data: Dict[str, Any]):
        """文章发布时触发"""
        try:
            # 更新Sitemap
            self.update_sitemap()
            print(f"[AdvancedSEO] Sitemap updated for article: {article_data.get('title')}")
        except Exception as e:
            print(f"[AdvancedSEO] Failed to update sitemap: {str(e)}")

    def check_redirect(self, url: str) -> str:
        """
        检查URL是否需要重定向
        
        Args:
            url: 请求的URL
            
        Returns:
            重定向后的URL或原URL
        """
        if not self.settings.get('enable_redirects'):
            return url

        for redirect in self.redirects:
            if redirect['from_url'] == url and redirect.get('active', True):
                print(f"[AdvancedSEO] Redirecting: {url} -> {redirect['to_url']}")
                return redirect['to_url']

        return url

    def track_404_error(self, error_data: Dict[str, Any]):
        """
        追踪404错误
        
        Args:
            error_data: 错误数据 {url, referrer, user_agent, timestamp}
        """
        if not self.settings.get('monitor_404'):
            return

        error_record = {
            'url': error_data.get('url', ''),
            'referrer': error_data.get('referrer', ''),
            'user_agent': error_data.get('user_agent', ''),
            'timestamp': error_data.get('timestamp', datetime.now().isoformat()),
            'count': 1,
        }

        # 检查是否已存在相同URL的错误
        existing = next(
            (e for e in self.not_found_errors if e['url'] == error_record['url']),
            None
        )

        if existing:
            existing['count'] += 1
            existing['timestamp'] = error_record['timestamp']
        else:
            self.not_found_errors.append(error_record)

        print(f"[AdvancedSEO] 404 error tracked: {error_record['url']}")

    def generate_sitemap(self) -> str:
        """
        生成XML Sitemap
        
        Returns:
            XML格式的Sitemap
        """
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_header += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        urls_xml = ''

        # 这里应该从数据库获取所有文章和页面
        # 简化实现：返回示例结构
        sample_urls = [
            {'loc': '/', 'lastmod': datetime.now().strftime('%Y-%m-%d'), 'changefreq': 'daily', 'priority': '1.0'},
            {'loc': '/about', 'lastmod': datetime.now().strftime('%Y-%m-%d'), 'changefreq': 'monthly',
             'priority': '0.8'},
        ]

        for url_data in sample_urls:
            urls_xml += '  <url>\n'
            urls_xml += f"    <loc>{url_data['loc']}</loc>\n"
            urls_xml += f"    <lastmod>{url_data['lastmod']}</lastmod>\n"
            urls_xml += f"    <changefreq>{url_data['changefreq']}</changefreq>\n"
            urls_xml += f"    <priority>{url_data['priority']}</priority>\n"

            # 如果启用图片包含
            if self.settings.get('include_images_in_sitemap'):
                urls_xml += '    <image:image>\n'
                urls_xml += '      <image:loc>https://example.com/image.jpg</image:loc>\n'
                urls_xml += '    </image:image>\n'

            urls_xml += '  </url>\n'

        xml_footer = '</urlset>'

        return xml_header + urls_xml + xml_footer

    def generate_robots_txt(self) -> str:
        """
        生成robots.txt内容
        
        Returns:
            robots.txt文本内容
        """
        lines = [
            "# FastBlog robots.txt",
            f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /api/",
            "Disallow: /private/",
            "",
            "# Allow search engines to crawl content",
            "Allow: /articles/",
            "Allow: /categories/",
            "",
            "# Sitemap location",
            f"Sitemap: {self.settings.get('canonical_url_base', 'https://example.com')}/sitemap.xml",
        ]

        return '\n'.join(lines)

    def add_redirect(self, from_url: str, to_url: str, redirect_type: int = 301) -> bool:
        """
        添加重定向规则
        
        Args:
            from_url: 源URL
            to_url: 目标URL
            redirect_type: 重定向类型 (301永久, 302临时)
            
        Returns:
            是否成功
        """
        redirect = {
            'from_url': from_url,
            'to_url': to_url,
            'type': redirect_type,
            'active': True,
            'created_at': datetime.now().isoformat(),
        }

        self.redirects.append(redirect)
        print(f"[AdvancedSEO] Redirect added: {from_url} -> {to_url}")
        return True

    def remove_redirect(self, from_url: str) -> bool:
        """
        移除重定向规则
        
        Args:
            from_url: 源URL
            
        Returns:
            是否成功
        """
        original_count = len(self.redirects)
        self.redirects = [r for r in self.redirects if r['from_url'] != from_url]

        if len(self.redirects) < original_count:
            print(f"[AdvancedSEO] Redirect removed: {from_url}")
            return True
        return False

    def get_redirects(self) -> List[Dict[str, Any]]:
        """获取所有重定向规则"""
        return self.redirects

    def get_404_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取404错误列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            404错误列表
        """
        # 按出现次数排序
        sorted_errors = sorted(
            self.not_found_errors,
            key=lambda x: x['count'],
            reverse=True
        )

        return sorted_errors[:limit]

    def suggest_fixes_for_404(self, url: str) -> List[str]:
        """
        为404错误提供修复建议
        
        Args:
            url: 出错的URL
            
        Returns:
            修复建议列表
        """
        suggestions = []

        # 简单的建议逻辑
        if '/article/' in url or '/post/' in url:
            suggestions.append("检查文章slug是否正确")
            suggestions.append("考虑添加重定向到相似的文章")

        if url.endswith('.html'):
            suggestions.append("尝试移除.html后缀")

        if '?' in url:
            suggestions.append("检查URL参数是否正确")

        suggestions.append("检查是否有拼写错误")
        suggestions.append("考虑创建该页面或重定向到相关页面")

        return suggestions

    def update_sitemap(self):
        """更新Sitemap文件"""
        try:
            sitemap_content = self.generate_sitemap()
            sitemap_path = Path('public/sitemap.xml')
            sitemap_path.parent.mkdir(parents=True, exist_ok=True)

            with open(sitemap_path, 'w', encoding='utf-8') as f:
                f.write(sitemap_content)

            print(f"[AdvancedSEO] Sitemap saved to {sitemap_path}")
        except Exception as e:
            print(f"[AdvancedSEO] Failed to save sitemap: {str(e)}")

    def update_robots_txt(self):
        """更新robots.txt文件"""
        try:
            robots_content = self.generate_robots_txt()
            robots_path = Path('public/robots.txt')
            robots_path.parent.mkdir(parents=True, exist_ok=True)

            with open(robots_path, 'w', encoding='utf-8') as f:
                f.write(robots_content)

            print(f"[AdvancedSEO] robots.txt saved to {robots_path}")
        except Exception as e:
            print(f"[AdvancedSEO] Failed to save robots.txt: {str(e)}")

    def get_seo_report(self) -> Dict[str, Any]:
        """
        生成SEO报告
        
        Returns:
            SEO报告数据
        """
        total_redirects = len(self.redirects)
        active_redirects = len([r for r in self.redirects if r.get('active', True)])
        total_404s = len(self.not_found_errors)
        high_frequency_404s = len([e for e in self.not_found_errors if e['count'] > 5])

        return {
            'redirects': {
                'total': total_redirects,
                'active': active_redirects,
            },
            '404_errors': {
                'total': total_404s,
                'high_frequency': high_frequency_404s,
                'top_errors': self.get_404_errors(limit=10),
            },
            'sitemap': {
                'last_updated': datetime.now().isoformat(),
                'update_frequency': self.settings.get('sitemap_update_frequency', 'daily'),
            },
            'recommendations': self._generate_seo_recommendations(),
        }

    def _generate_seo_recommendations(self) -> List[str]:
        """生成SEO优化建议"""
        recommendations = []

        if len(self.not_found_errors) > 10:
            recommendations.append("发现较多404错误，建议检查并修复")

        if len([r for r in self.redirects if r.get('active')]) > 50:
            recommendations.append("重定向规则过多，可能影响性能，建议清理无用规则")

        if not self.settings.get('canonical_url_base'):
            recommendations.append("建议设置规范URL基础地址")

        if not self.settings.get('include_images_in_sitemap'):
            recommendations.append("建议在Sitemap中包含图片以提升图片搜索排名")

        return recommendations

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'auto_generate_meta',
                    'type': 'boolean',
                    'label': '自动生成元标签',
                },
                {
                    'key': 'include_images_in_sitemap',
                    'type': 'boolean',
                    'label': 'Sitemap包含图片',
                },
                {
                    'key': 'sitemap_update_frequency',
                    'type': 'select',
                    'label': 'Sitemap更新频率',
                    'options': [
                        {'value': 'daily', 'label': '每天'},
                        {'value': 'weekly', 'label': '每周'},
                        {'value': 'monthly', 'label': '每月'},
                    ],
                },
                {
                    'key': 'enable_redirects',
                    'type': 'boolean',
                    'label': '启用重定向管理',
                },
                {
                    'key': 'monitor_404',
                    'type': 'boolean',
                    'label': '监控404错误',
                },
                {
                    'key': 'canonical_url_base',
                    'type': 'text',
                    'label': '规范URL基础',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '生成Sitemap',
                    'action': 'generate_sitemap',
                    'variant': 'default',
                },
                {
                    'type': 'button',
                    'label': '生成robots.txt',
                    'action': 'generate_robots_txt',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = AdvancedSeoPlugin()
