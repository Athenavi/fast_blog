"""
SEO优化服务
包含站点地图、结构化数据、面包屑、Canonical URL
"""

from datetime import datetime
from typing import Dict, Any, List
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring


class SEOService:
    """
    SEO服务
    
    功能:
    1. XML站点地图生成
    2. Schema.org结构化数据
    3. 面包屑导航
    4. Canonical URL处理
    """

    def __init__(self, base_url: str = "https://example.com"):
        self.base_url = base_url

    # ==================== XML站点地图 ====================

    def generate_sitemap(
            self,
            articles: List[Dict[str, Any]],
            categories: List[Dict[str, Any]] = None,
            pages: List[Dict[str, Any]] = None
    ) -> str:
        """
        生成XML站点地图
        
        Args:
            articles: 文章列表
            categories: 分类列表
            pages: 页面列表
            
        Returns:
            XML字符串
        """
        urlset = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        # 添加首页
        self._add_url(urlset, self.base_url, '1.0', 'daily')

        # 添加文章
        for article in articles:
            loc = f"{self.base_url}/articles/{article.get('slug', article.get('id'))}"
            priority = '0.8' if article.get('is_featured') else '0.6'
            changefreq = 'weekly'

            self._add_url(
                urlset,
                loc,
                priority,
                changefreq,
                article.get('updated_at') or article.get('created_at')
            )

        # 添加分类
        if categories:
            for category in categories:
                loc = f"{self.base_url}/categories/{category.get('slug', category.get('id'))}"
                self._add_url(urlset, loc, '0.7', 'weekly')

        # 添加页面
        if pages:
            for page in pages:
                loc = f"{self.base_url}/pages/{page.get('slug', page.get('id'))}"
                self._add_url(urlset, loc, '0.5', 'monthly')

        # 格式化XML
        rough_string = tostring(urlset, encoding='unicode')
        dom = parseString(rough_string)
        return dom.toprettyxml(indent="  ")

    def _add_url(
            self,
            urlset: Element,
            loc: str,
            priority: str = '0.5',
            changefreq: str = 'monthly',
            lastmod: str = None
    ):
        """添加URL到站点地图"""
        url_elem = SubElement(urlset, 'url')

        loc_elem = SubElement(url_elem, 'loc')
        loc_elem.text = loc

        if lastmod:
            try:
                # 格式化日期
                if isinstance(lastmod, str):
                    dt = datetime.fromisoformat(lastmod.replace('Z', '+00:00'))
                else:
                    dt = lastmod
                lastmod_elem = SubElement(url_elem, 'lastmod')
                lastmod_elem.text = dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            except:
                pass

        changefreq_elem = SubElement(url_elem, 'changefreq')
        changefreq_elem.text = changefreq

        priority_elem = SubElement(url_elem, 'priority')
        priority_elem.text = priority

    # ==================== Schema.org结构化数据 ====================

    def generate_article_schema(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成文章结构化数据
        
        Args:
            article: 文章数据
            
        Returns:
            Schema.org JSON-LD数据
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article.get('title', ''),
            "description": article.get('excerpt', ''),
            "image": article.get('cover_image', ''),
            "datePublished": article.get('created_at', ''),
            "dateModified": article.get('updated_at', ''),
            "author": {
                "@type": "Person",
                "name": article.get('author_name', '')
            },
            "publisher": {
                "@type": "Organization",
                "name": "FastBlog",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{self.base_url}/logo.png"
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{self.base_url}/articles/{article.get('slug', article.get('id'))}"
            }
        }

        return schema

    def generate_breadcrumb_schema(self, breadcrumbs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        生成面包屑结构化数据
        
        Args:
            breadcrumbs: 面包屑列表 [{'name': '...', 'url': '...'}]
            
        Returns:
            Schema.org JSON-LD数据
        """
        item_list_elements = []

        for i, crumb in enumerate(breadcrumbs, 1):
            item_list_elements.append({
                "@type": "ListItem",
                "position": i,
                "name": crumb['name'],
                "item": crumb['url']
            })

        schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": item_list_elements
        }

        return schema

    # ==================== 面包屑导航 ====================

    def generate_breadcrumbs(
            self,
            article: Dict[str, Any] = None,
            category: Dict[str, Any] = None
    ) -> List[Dict[str, str]]:
        """
        生成面包屑导航
        
        Args:
            article: 文章数据
            category: 分类数据
            
        Returns:
            面包屑列表
        """
        breadcrumbs = [
            {'name': '首页', 'url': self.base_url}
        ]

        if category:
            breadcrumbs.append({
                'name': category.get('name', ''),
                'url': f"{self.base_url}/categories/{category.get('slug', '')}"
            })

        if article:
            if article.get('category_name'):
                breadcrumbs.append({
                    'name': article.get('category_name', ''),
                    'url': f"{self.base_url}/categories/{article.get('category_slug', '')}"
                })

            breadcrumbs.append({
                'name': article.get('title', ''),
                'url': f"{self.base_url}/articles/{article.get('slug', '')}"
            })

        return breadcrumbs

    # ==================== Canonical URL ====================

    def get_canonical_url(
            self,
            path: str,
            params: Dict[str, Any] = None
    ) -> str:
        """
        获取规范URL
        
        Args:
            path: 路径
            params: 查询参数(会被移除)
            
        Returns:
            规范URL
        """
        # Canonical URL不包含查询参数
        return f"{self.base_url}{path}"

    def generate_canonical_tag(self, path: str, params: Dict[str, Any] = None) -> str:
        """
        生成Canonical标签
        
        Args:
            path: 路径
            params: 查询参数
            
        Returns:
            HTML link标签
        """
        canonical_url = self.get_canonical_url(path, params)
        return f'<link rel="canonical" href="{canonical_url}" />'

    # ==================== SEO分析和评分 ====================

    def analyze_article_seo(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析文章SEO并给出评分和建议
        
        Args:
            article: 文章数据 {title, excerpt, content, cover_image, tags, ...}
            
        Returns:
            SEO分析报告 {score, checks, suggestions}
        """
        checks = []
        suggestions = []
        score = 100

        # 1. 标题长度检查
        title = article.get('title', '')
        title_length = len(title)
        if title_length < 30:
            checks.append(
                {'item': '标题长度', 'status': 'warning', 'message': f'标题过短 ({title_length}字符)，建议30-60字符'})
            suggestions.append('增加标题长度，包含更多关键词')
            score -= 10
        elif title_length > 60:
            checks.append(
                {'item': '标题长度', 'status': 'warning', 'message': f'标题过长 ({title_length}字符)，建议30-60字符'})
            suggestions.append('缩短标题，确保在搜索结果中完整显示')
            score -= 10
        else:
            checks.append({'item': '标题长度', 'status': 'pass', 'message': f'标题长度合适 ({title_length}字符)'})

        # 2. 描述长度检查
        excerpt = article.get('excerpt', '')
        excerpt_length = len(excerpt)
        if not excerpt:
            checks.append({'item': '文章摘要', 'status': 'fail', 'message': '缺少文章摘要'})
            suggestions.append('添加文章摘要（150-160字符），用于搜索引擎展示')
            score -= 20
        elif excerpt_length < 120:
            checks.append({'item': '文章摘要', 'status': 'warning', 'message': f'摘要过短 ({excerpt_length}字符)'})
            suggestions.append('扩展摘要到150-160字符')
            score -= 10
        elif excerpt_length > 160:
            checks.append({'item': '文章摘要', 'status': 'warning', 'message': f'摘要过长 ({excerpt_length}字符)'})
            suggestions.append('精简摘要到150-160字符')
            score -= 5
        else:
            checks.append({'item': '文章摘要', 'status': 'pass', 'message': f'摘要长度合适 ({excerpt_length}字符)'})

        # 3. 封面图片检查
        cover_image = article.get('cover_image', '')
        if not cover_image:
            checks.append({'item': '封面图片', 'status': 'warning', 'message': '缺少封面图片'})
            suggestions.append('添加封面图片，提升点击率')
            score -= 10
        else:
            checks.append({'item': '封面图片', 'status': 'pass', 'message': '已设置封面图片'})

        # 4. 内容长度检查
        content = article.get('content', '')
        content_length = len(content)
        word_count = len(content.split()) if content else 0
        if word_count < 300:
            checks.append({'item': '内容长度', 'status': 'warning', 'message': f'内容过短 ({word_count}字)'})
            suggestions.append('增加内容长度，建议至少600字以上')
            score -= 15
        elif word_count < 600:
            checks.append({'item': '内容长度', 'status': 'warning', 'message': f'内容较短 ({word_count}字)'})
            suggestions.append('继续丰富内容，建议达到1000字以上')
            score -= 5
        else:
            checks.append({'item': '内容长度', 'status': 'pass', 'message': f'内容长度充足 ({word_count}字)'})

        # 5. 标签检查
        tags = article.get('tags', [])
        tag_count = len(tags) if isinstance(tags, list) else 0
        if tag_count == 0:
            checks.append({'item': '标签', 'status': 'warning', 'message': '未设置标签'})
            suggestions.append('添加3-5个相关标签，提升分类和搜索')
            score -= 10
        elif tag_count > 10:
            checks.append({'item': '标签', 'status': 'warning', 'message': f'标签过多 ({tag_count}个)'})
            suggestions.append('减少标签数量，建议3-5个精准标签')
            score -= 5
        else:
            checks.append({'item': '标签', 'status': 'pass', 'message': f'标签数量合适 ({tag_count}个)'})

        # 6. URL Slug检查
        slug = article.get('slug', '')
        if not slug:
            checks.append({'item': 'URL Slug', 'status': 'fail', 'message': '缺少URL Slug'})
            suggestions.append('设置友好的URL Slug（使用英文或拼音）')
            score -= 15
        elif len(slug) > 100:
            checks.append({'item': 'URL Slug', 'status': 'warning', 'message': 'URL Slug过长'})
            suggestions.append('缩短URL Slug，保持简洁')
            score -= 5
        else:
            checks.append({'item': 'URL Slug', 'status': 'pass', 'message': 'URL Slug设置合理'})

        # 7. 内部链接检查（简单检测）
        internal_links = content.count(f'{self.base_url}/') if content else 0
        if internal_links == 0 and word_count > 500:
            checks.append({'item': '内部链接', 'status': 'warning', 'message': '缺少内部链接'})
            suggestions.append('添加2-3个相关文章的内部链接')
            score -= 5
        else:
            checks.append({'item': '内部链接', 'status': 'pass', 'message': f'包含{internal_links}个内部链接'})

        # 确保分数不低于0
        score = max(0, score)

        # 评级
        if score >= 90:
            grade = 'A'
        elif score >= 80:
            grade = 'B'
        elif score >= 70:
            grade = 'C'
        elif score >= 60:
            grade = 'D'
        else:
            grade = 'F'

        return {
            'score': score,
            'grade': grade,
            'checks': checks,
            'suggestions': suggestions,
            'total_checks': len(checks),
            'passed_checks': len([c for c in checks if c['status'] == 'pass']),
            'warnings': len([c for c in checks if c['status'] == 'warning']),
            'failures': len([c for c in checks if c['status'] == 'fail'])
        }


# 全局实例
seo_service = SEOService()
