"""
结构化数据标记插件
自动生成Schema.org结构化数据，提升搜索引擎理解
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class SchemaMarkupPlugin(BasePlugin):
    """
    结构化数据标记插件
    
    功能:
    1. Article结构化数据
    2. Breadcrumb导航标记
    3. Organization信息标记
    4. FAQ结构化数据
    5. Review评分标记
    6. 自定义Schema支持
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="结构化数据标记",
            slug="schema-markup",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_schema': True,
            'enable_article': True,
            'enable_breadcrumb': True,
            'enable_organization': True,
            'enable_faq': True,
            'enable_review': True,
            'enable_product': False,
            'enable_event': False,
            'organization_name': '',
            'organization_logo': '',
            'organization_url': '',
            'social_profiles': [],
            'default_article_type': 'Article',  # Article, BlogPosting, NewsArticle
            'include_author_info': True,
            'include_publish_date': True,
            'include_modify_date': True,
        }

        # 统计
        self.stats = {
            'total_schemas_generated': 0,
            'by_type': {},
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章页面注入Schema
        plugin_hooks.add_action(
            "article_page_head",
            self.inject_article_schema,
            priority=10
        )

        # 页面头部注入通用Schema
        plugin_hooks.add_action(
            "page_head",
            self.inject_general_schema,
            priority=10
        )

        # 面包屑导航
        plugin_hooks.add_filter(
            "breadcrumb_data",
            self.generate_breadcrumb_schema,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[SchemaMarkup] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[SchemaMarkup] Plugin deactivated")

    def inject_article_schema(self, context: Dict[str, Any]):
        """
        注入文章Schema
        
        Args:
            context: 上下文数据 {article, page_type}
        """
        if not self.settings.get('enable_schema') or not self.settings.get('enable_article'):
            return

        article = context.get('article')
        if not article:
            return

        schema = self.generate_article_schema(article)
        
        if schema:
            script_tag = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
            
            if 'schema_scripts' not in context:
                context['schema_scripts'] = []
            
            context['schema_scripts'].append(script_tag)
            self._update_stats('Article')

    def inject_general_schema(self, context: Dict[str, Any]):
        """
        注入通用Schema
        
        Args:
            context: 上下文数据 {page_type, site_info}
        """
        if not self.settings.get('enable_schema'):
            return

        scripts = []

        # 组织信息Schema
        if self.settings.get('enable_organization'):
            org_schema = self.generate_organization_schema()
            if org_schema:
                scripts.append(f'<script type="application/ld+json">{json.dumps(org_schema, ensure_ascii=False)}</script>')
                self._update_stats('Organization')

        # 网站搜索Schema
        website_schema = self.generate_website_schema()
        if website_schema:
            scripts.append(f'<script type="application/ld+json">{json.dumps(website_schema, ensure_ascii=False)}</script>')
            self._update_stats('WebSite')

        # 添加到上下文
        if scripts:
            if 'schema_scripts' not in context:
                context['schema_scripts'] = []
            context['schema_scripts'].extend(scripts)

    def generate_breadcrumb_schema(self, breadcrumb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成面包屑Schema
        
        Args:
            breadcrumb_data: 面包屑数据 {items: [{name, url}]}
            
        Returns:
            包含Schema的面包屑数据
        """
        if not self.settings.get('enable_schema') or not self.settings.get('enable_breadcrumb'):
            return breadcrumb_data

        items = breadcrumb_data.get('items', [])
        if not items:
            return breadcrumb_data

        schema = {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': []
        }

        for index, item in enumerate(items, 1):
            schema['itemListElement'].append({
                '@type': 'ListItem',
                'position': index,
                'name': item.get('name', ''),
                'item': item.get('url', '')
            })

        breadcrumb_data['schema'] = schema
        self._update_stats('BreadcrumbList')
        
        return breadcrumb_data

    def generate_article_schema(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成文章Schema
        
        Args:
            article: 文章数据
            
        Returns:
            Schema对象
        """
        try:
            article_type = self.settings.get('default_article_type', 'Article')
            
            schema = {
                '@context': 'https://schema.org',
                '@type': article_type,
                'headline': article.get('title', ''),
                'description': article.get('excerpt', article.get('description', '')),
                'url': article.get('url', ''),
            }

            # 添加图片
            if article.get('featured_image'):
                schema['image'] = [article['featured_image']]
            elif article.get('images'):
                schema['image'] = article['images'][:3]

            # 添加作者
            if self.settings.get('include_author_info') and article.get('author'):
                author = article['author']
                schema['author'] = {
                    '@type': 'Person',
                    'name': author.get('name', ''),
                }
                if author.get('url'):
                    schema['author']['url'] = author['url']
                if author.get('avatar'):
                    schema['author']['image'] = author['avatar']

            # 添加发布者
            if self.settings.get('enable_organization'):
                schema['publisher'] = {
                    '@type': 'Organization',
                    'name': self.settings.get('organization_name', ''),
                }
                if self.settings.get('organization_logo'):
                    schema['publisher']['logo'] = {
                        '@type': 'ImageObject',
                        'url': self.settings['organization_logo']
                    }

            # 添加日期
            if self.settings.get('include_publish_date'):
                publish_date = article.get('publish_date') or article.get('created_at')
                if publish_date:
                    schema['datePublished'] = self._format_date(publish_date)

            if self.settings.get('include_modify_date'):
                modify_date = article.get('modified_at') or article.get('updated_at')
                if modify_date:
                    schema['dateModified'] = self._format_date(modify_date)

            # 添加分类和标签
            if article.get('category'):
                schema['articleSection'] = article['category']
            
            if article.get('tags'):
                schema['keywords'] = ', '.join(article['tags'])

            # 添加评论数
            if article.get('comment_count') is not None:
                schema['commentCount'] = article['comment_count']

            # 添加阅读时间
            if article.get('reading_time'):
                schema['timeRequired'] = f"PT{article['reading_time']}M"

            return schema

        except Exception as e:
            print(f"[SchemaMarkup] Error generating article schema: {e}")
            return None

    def generate_organization_schema(self) -> Optional[Dict[str, Any]]:
        """
        生成组织Schema
        
        Returns:
            Schema对象
        """
        org_name = self.settings.get('organization_name', '')
        if not org_name:
            return None

        schema = {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': org_name,
            'url': self.settings.get('organization_url', ''),
        }

        # 添加Logo
        if self.settings.get('organization_logo'):
            schema['logo'] = {
                '@type': 'ImageObject',
                'url': self.settings['organization_logo']
            }

        # 添加社交媒体
        social_profiles = self.settings.get('social_profiles', [])
        if social_profiles:
            schema['sameAs'] = social_profiles

        # 添加联系信息
        if self.settings.get('contact_email'):
            schema['email'] = self.settings['contact_email']
        
        if self.settings.get('contact_phone'):
            schema['telephone'] = self.settings['contact_phone']

        # 添加地址
        if self.settings.get('address'):
            schema['address'] = {
                '@type': 'PostalAddress',
                **self.settings['address']
            }

        return schema

    def generate_website_schema(self) -> Dict[str, Any]:
        """
        生成网站Schema
        
        Returns:
            Schema对象
        """
        schema = {
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            'name': self.settings.get('site_name', ''),
            'url': self.settings.get('site_url', ''),
        }

        # 添加搜索功能
        if self.settings.get('enable_search'):
            schema['potentialAction'] = {
                '@type': 'SearchAction',
                'target': {
                    '@type': 'EntryPoint',
                    'urlTemplate': f"{self.settings.get('site_url', '')}/search?q={search_term_string}"
                },
                'query-input': 'required name=search_term_string'
            }

        return schema

    def generate_faq_schema(self, faqs: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        生成FAQ Schema
        
        Args:
            faqs: FAQ列表 [{question, answer}]
            
        Returns:
            Schema对象
        """
        if not self.settings.get('enable_schema') or not self.settings.get('enable_faq'):
            return None

        if not faqs:
            return None

        schema = {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'mainEntity': []
        }

        for faq in faqs:
            schema['mainEntity'].append({
                '@type': 'Question',
                'name': faq.get('question', ''),
                'acceptedAnswer': {
                    '@type': 'Answer',
                    'text': faq.get('answer', '')
                }
            })

        self._update_stats('FAQPage')
        return schema

    def generate_review_schema(self, review_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成评价Schema
        
        Args:
            review_data: 评价数据 {rating, author, date, content}
            
        Returns:
            Schema对象
        """
        if not self.settings.get('enable_schema') or not self.settings.get('enable_review'):
            return None

        rating = review_data.get('rating', 0)
        if not rating:
            return None

        schema = {
            '@context': 'https://schema.org',
            '@type': 'Review',
            'reviewRating': {
                '@type': 'Rating',
                'ratingValue': rating,
                'bestRating': review_data.get('max_rating', 5),
                'worstRating': review_data.get('min_rating', 1)
            },
            'author': {
                '@type': 'Person',
                'name': review_data.get('author', 'Anonymous')
            },
            'datePublished': self._format_date(review_data.get('date', datetime.now()))
        }

        if review_data.get('content'):
            schema['reviewBody'] = review_data['content']

        if review_data.get('item_reviewed'):
            schema['itemReviewed'] = review_data['item_reviewed']

        self._update_stats('Review')
        return schema

    def generate_product_schema(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成产品Schema
        
        Args:
            product: 产品数据
            
        Returns:
            Schema对象
        """
        if not self.settings.get('enable_product'):
            return None

        schema = {
            '@context': 'https://schema.org',
            '@type': 'Product',
            'name': product.get('name', ''),
            'description': product.get('description', ''),
        }

        # 添加图片
        if product.get('image'):
            schema['image'] = product['image']

        # 添加品牌
        if product.get('brand'):
            schema['brand'] = {
                '@type': 'Brand',
                'name': product['brand']
            }

        # 添加价格
        if product.get('price') is not None:
            schema['offers'] = {
                '@type': 'Offer',
                'price': product['price'],
                'priceCurrency': product.get('currency', 'USD'),
                'availability': 'https://schema.org/' + product.get('availability', 'InStock')
            }

        # 添加评分
        if product.get('rating'):
            schema['aggregateRating'] = {
                '@type': 'AggregateRating',
                'ratingValue': product['rating'],
                'reviewCount': product.get('review_count', 0)
            }

        self._update_stats('Product')
        return schema

    def generate_event_schema(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生活动Schema
        
        Args:
            event: 活动数据
            
        Returns:
            Schema对象
        """
        if not self.settings.get('enable_event'):
            return None

        schema = {
            '@context': 'https://schema.org',
            '@type': 'Event',
            'name': event.get('name', ''),
            'description': event.get('description', ''),
            'startDate': self._format_date(event.get('start_date')),
            'endDate': self._format_date(event.get('end_date')),
        }

        # 添加地点
        if event.get('location'):
            schema['location'] = {
                '@type': 'Place',
                'name': event['location'].get('name', ''),
                'address': event['location'].get('address', '')
            }

        # 添加组织者
        if event.get('organizer'):
            schema['organizer'] = {
                '@type': 'Organization',
                'name': event['organizer']
            }

        # 添加票价
        if event.get('price'):
            schema['offers'] = {
                '@type': 'Offer',
                'price': event['price'],
                'priceCurrency': event.get('currency', 'USD'),
                'url': event.get('ticket_url', '')
            }

        self._update_stats('Event')
        return schema

    def get_custom_schema(self, schema_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成自定义Schema
        
        Args:
            schema_type: Schema类型
            data: 数据
            
        Returns:
            Schema对象
        """
        schema = {
            '@context': 'https://schema.org',
            '@type': schema_type,
            **data
        }

        self._update_stats(schema_type)
        return schema

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        return {
            'enabled': self.settings.get('enable_schema'),
            'total_generated': self.stats['total_schemas_generated'],
            'by_type': self.stats['by_type'],
            'settings': self.settings,
        }

    def validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证Schema有效性
        
        Args:
            schema: Schema对象
            
        Returns:
            验证结果 {valid: bool, errors: []}
        """
        errors = []

        # 检查必需字段
        if '@context' not in schema:
            errors.append('Missing @context field')
        
        if '@type' not in schema:
            errors.append('Missing @type field')

        # 检查@context是否正确
        if schema.get('@context') != 'https://schema.org':
            errors.append('Invalid @context. Should be https://schema.org')

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _format_date(self, date_value) -> str:
        """
        格式化日期为ISO 8601格式
        
        Args:
            date_value: 日期值
            
        Returns:
            ISO格式日期字符串
        """
        if isinstance(date_value, str):
            return date_value
        elif isinstance(date_value, datetime):
            return date_value.isoformat()
        else:
            return str(date_value)

    def _update_stats(self, schema_type: str):
        """更新统计"""
        self.stats['total_schemas_generated'] += 1
        self.stats['by_type'][schema_type] = self.stats['by_type'].get(schema_type, 0) + 1

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_schema',
                    'type': 'boolean',
                    'label': '启用结构化数据',
                },
                {
                    'key': 'enable_article',
                    'type': 'boolean',
                    'label': '文章Schema',
                },
                {
                    'key': 'enable_breadcrumb',
                    'type': 'boolean',
                    'label': '面包屑Schema',
                },
                {
                    'key': 'enable_organization',
                    'type': 'boolean',
                    'label': '组织信息Schema',
                },
                {
                    'key': 'enable_faq',
                    'type': 'boolean',
                    'label': 'FAQ Schema',
                },
                {
                    'key': 'enable_review',
                    'type': 'boolean',
                    'label': '评价Schema',
                },
                {
                    'key': 'organization_name',
                    'type': 'text',
                    'label': '组织名称',
                    'show_if': {'enable_organization': True},
                },
                {
                    'key': 'organization_url',
                    'type': 'url',
                    'label': '组织网址',
                    'show_if': {'enable_organization': True},
                },
                {
                    'key': 'organization_logo',
                    'type': 'image',
                    'label': '组织Logo',
                    'show_if': {'enable_organization': True},
                },
                {
                    'key': 'default_article_type',
                    'type': 'select',
                    'label': '默认文章类型',
                    'options': [
                        {'value': 'Article', 'label': 'Article'},
                        {'value': 'BlogPosting', 'label': 'BlogPosting'},
                        {'value': 'NewsArticle', 'label': 'NewsArticle'},
                    ],
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看统计',
                    'action': 'view_stats',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '测试Schema',
                    'action': 'test_schema',
                    'variant': 'primary',
                },
            ]
        }


# 插件实例
plugin_instance = SchemaMarkupPlugin()
