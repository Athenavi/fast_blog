"""
相关内容增强插件 (Related Content)
提供智能推荐相关文章、手动推荐设置、相关内容小部件和A/B测试推荐算法
"""

from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class RelatedContentPlugin(BasePlugin):
    """
    相关内容增强插件
    
    功能:
    1. AI推荐相关文章 - 基于标签/分类/相似度/热度
    2. 手动推荐设置 - 管理员可手动指定相关文章
    3. 相关内容小部件 - 侧边栏或文章底部展示
    4. A/B测试推荐算法 - 测试不同算法效果
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="相关内容增强",
            slug="related-content",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'recommendation_algorithm': 'tags',
            'max_related_posts': 5,
            'show_thumbnail': True,
            'show_excerpt': True,
            'enable_manual_override': True,
            'widget_position': 'bottom',
        }

        # 模拟文章数据库(实际应从数据库获取)
        self.articles_db = []

        # 手动推荐映射 {article_id: [related_article_ids]}
        self.manual_recommendations: Dict[str, List[str]] = {}

        # A/B测试数据
        self.ab_test_data = {
            'enabled': False,
            'test_groups': {},
            'results': {},
        }

        # 推荐统计
        self.recommendation_stats = {
            'total_recommendations': 0,
            'total_clicks': 0,
            'by_algorithm': {},
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章页面加载时获取相关内容
        plugin_hooks.add_filter(
            "article_related_posts",
            self.get_related_posts,
            priority=10
        )

        # 追踪推荐点击
        plugin_hooks.add_action(
            "related_post_clicked",
            self.track_click,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[RelatedContent] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[RelatedContent] Plugin deactivated")

    def get_related_posts(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取相关文章
        
        Args:
            context: 上下文 {article_id, tags, categories, content}
            
        Returns:
            相关文章列表
        """
        article_id = context.get('article_id', '')

        # 检查是否有手动推荐
        if self.settings.get('enable_manual_override') and article_id in self.manual_recommendations:
            manual_ids = self.manual_recommendations[article_id]
            related = self._get_articles_by_ids(manual_ids)
            print(f"[RelatedContent] Using manual recommendations for {article_id}")
        else:
            # 使用自动推荐算法
            algorithm = self.settings.get('recommendation_algorithm', 'tags')
            related = self._recommend_by_algorithm(article_id, context, algorithm)

        # 限制数量
        max_count = self.settings.get('max_related_posts', 5)
        related = related[:max_count]

        # 更新统计
        self.recommendation_stats['total_recommendations'] += len(related)

        return related

    def _recommend_by_algorithm(self, article_id: str, context: Dict[str, Any], algorithm: str) -> List[Dict[str, Any]]:
        """
        根据算法推荐相关文章
        
        Args:
            article_id: 当前文章ID
            context: 文章上下文
            algorithm: 推荐算法
            
        Returns:
            推荐文章列表
        """
        if algorithm == 'tags':
            return self._recommend_by_tags(context)
        elif algorithm == 'categories':
            return self._recommend_by_categories(context)
        elif algorithm == 'similarity':
            return self._recommend_by_similarity(context)
        elif algorithm == 'popular':
            return self._recommend_by_popularity()
        else:
            return self._recommend_by_tags(context)

    def _recommend_by_tags(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于标签推荐"""
        current_tags = context.get('tags', [])
        if not current_tags:
            return []

        # 计算每篇文章的标签匹配度
        scored_articles = []
        for article in self.articles_db:
            if article['id'] == context.get('article_id'):
                continue

            article_tags = set(article.get('tags', []))
            current_tag_set = set(current_tags)

            # 计算交集
            common_tags = article_tags & current_tag_set
            score = len(common_tags)

            if score > 0:
                scored_articles.append((article, score))

        # 按分数排序
        scored_articles.sort(key=lambda x: x[1], reverse=True)
        return [article for article, score in scored_articles]

    def _recommend_by_categories(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于分类推荐"""
        current_categories = context.get('categories', [])
        if not current_categories:
            return []

        scored_articles = []
        for article in self.articles_db:
            if article['id'] == context.get('article_id'):
                continue

            article_categories = set(article.get('categories', []))
            current_cat_set = set(current_categories)

            common_cats = article_categories & current_cat_set
            score = len(common_cats)

            if score > 0:
                scored_articles.append((article, score))

        scored_articles.sort(key=lambda x: x[1], reverse=True)
        return [article for article, score in scored_articles]

    def _recommend_by_similarity(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于内容相似度推荐(简化版TF-IDF)"""
        current_content = context.get('content', '').lower()
        if not current_content:
            return []

        # 简单的词频分析
        current_words = set(current_content.split())

        scored_articles = []
        for article in self.articles_db:
            if article['id'] == context.get('article_id'):
                continue

            article_content = article.get('content', '').lower()
            article_words = set(article_content.split())

            # 计算词汇重叠度
            common_words = current_words & article_words
            score = len(common_words)

            if score > 0:
                scored_articles.append((article, score))

        scored_articles.sort(key=lambda x: x[1], reverse=True)
        return [article for article, score in scored_articles]

    def _recommend_by_popularity(self) -> List[Dict[str, Any]]:
        """基于热门文章推荐"""
        # 按浏览量排序
        sorted_articles = sorted(
            self.articles_db,
            key=lambda x: x.get('views', 0),
            reverse=True
        )
        return sorted_articles

    def set_manual_recommendations(self, article_id: str, related_ids: List[str]):
        """
        设置手动推荐
        
        Args:
            article_id: 文章ID
            related_ids: 相关文章ID列表
        """
        self.manual_recommendations[article_id] = related_ids
        print(f"[RelatedContent] Manual recommendations set for {article_id}: {related_ids}")

    def get_manual_recommendations(self, article_id: str) -> List[str]:
        """获取手动推荐"""
        return self.manual_recommendations.get(article_id, [])

    def track_click(self, click_data: Dict[str, Any]):
        """
        追踪推荐点击
        
        Args:
            click_data: {source_article_id, clicked_article_id, algorithm}
        """
        self.recommendation_stats['total_clicks'] += 1

        algorithm = click_data.get('algorithm', 'unknown')
        if algorithm not in self.recommendation_stats['by_algorithm']:
            self.recommendation_stats['by_algorithm'][algorithm] = {
                'impressions': 0,
                'clicks': 0,
            }

        self.recommendation_stats['by_algorithm'][algorithm]['clicks'] += 1

    def start_ab_test(self, algorithms: List[str], traffic_split: Dict[str, float]):
        """
        启动A/B测试
        
        Args:
            algorithms: 要测试的算法列表
            traffic_split: 流量分配 {algorithm: percentage}
        """
        self.ab_test_data['enabled'] = True
        self.ab_test_data['test_groups'] = {
            algo: {'traffic_pct': traffic_split.get(algo, 0), 'impressions': 0, 'clicks': 0}
            for algo in algorithms
        }
        self.ab_test_data['results'] = {}

        print(f"[RelatedContent] A/B test started with algorithms: {algorithms}")

    def stop_ab_test(self) -> Dict[str, Any]:
        """
        停止A/B测试并返回结果
        
        Returns:
            测试结果
        """
        if not self.ab_test_data['enabled']:
            return {'error': 'No active A/B test'}

        results = {}
        for algo, data in self.ab_test_data['test_groups'].items():
            impressions = data['impressions']
            clicks = data['clicks']
            ctr = round((clicks / impressions * 100) if impressions > 0 else 0, 2)

            results[algo] = {
                'impressions': impressions,
                'clicks': clicks,
                'ctr': ctr,
            }

        self.ab_test_data['enabled'] = False
        self.ab_test_data['results'] = results

        print(f"[RelatedContent] A/B test completed. Results: {results}")
        return results

    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐统计"""
        total_recs = self.recommendation_stats['total_recommendations']
        total_clicks = self.recommendation_stats['total_clicks']

        return {
            'total_recommendations': total_recs,
            'total_clicks': total_clicks,
            'overall_ctr': round((total_clicks / total_recs * 100) if total_recs > 0 else 0, 2),
            'by_algorithm': self.recommendation_stats['by_algorithm'],
            'ab_test_active': self.ab_test_data['enabled'],
        }

    def generate_widget_html(self, related_posts: List[Dict[str, Any]]) -> str:
        """
        生成小部件HTML
        
        Args:
            related_posts: 相关文章列表
            
        Returns:
            HTML代码
        """
        if not related_posts:
            return ''

        html = '<div class="related-posts-widget">\n'
        html += '  <h3>相关文章</h3>\n'
        html += '  <ul>\n'

        for post in related_posts:
            html += f'    <li>\n'

            # 缩略图
            if self.settings.get('show_thumbnail') and post.get('thumbnail'):
                html += f'      <img src="{post["thumbnail"]}" alt="{post["title"]}">\n'

            # 标题和链接
            html += f'      <a href="/article/{post["id"]}">{post["title"]}</a>\n'

            # 摘要
            if self.settings.get('show_excerpt') and post.get('excerpt'):
                html += f'      <p>{post["excerpt"][:100]}...</p>\n'

            html += f'    </li>\n'

        html += '  </ul>\n'
        html += '</div>\n'

        return html

    def _get_articles_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """根据ID获取文章"""
        return [article for article in self.articles_db if article['id'] in ids]

    def add_article_to_db(self, article: Dict[str, Any]):
        """添加文章到数据库(用于测试)"""
        self.articles_db.append(article)

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'recommendation_algorithm',
                    'type': 'select',
                    'label': '推荐算法',
                    'options': [
                        {'value': 'tags', 'label': '基于标签'},
                        {'value': 'categories', 'label': '基于分类'},
                        {'value': 'similarity', 'label': '内容相似度'},
                        {'value': 'popular', 'label': '热门文章'},
                    ],
                },
                {
                    'key': 'max_related_posts',
                    'type': 'number',
                    'label': '最大推荐数量',
                    'min': 1,
                    'max': 10,
                },
                {
                    'key': 'show_thumbnail',
                    'type': 'boolean',
                    'label': '显示缩略图',
                },
                {
                    'key': 'show_excerpt',
                    'type': 'boolean',
                    'label': '显示摘要',
                },
                {
                    'key': 'enable_manual_override',
                    'type': 'boolean',
                    'label': '允许手动覆盖',
                },
                {
                    'key': 'widget_position',
                    'type': 'select',
                    'label': '小部件位置',
                    'options': [
                        {'value': 'sidebar', 'label': '侧边栏'},
                        {'value': 'bottom', 'label': '文章底部'},
                        {'value': 'both', 'label': '两者'},
                    ],
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '启动A/B测试',
                    'action': 'start_ab_test',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = RelatedContentPlugin()
