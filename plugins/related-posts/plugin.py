"""
相关文章推荐插件
根据当前文章的分类和标签推荐相关文章
"""

from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class RelatedPostsPlugin(BasePlugin):
    """
    相关文章推荐插件
    
    功能:
    1. 基于分类的相关性推荐
    2. 基于标签的相关性推荐
    3. 基于浏览历史的推荐（预留）
    4. 可配置推荐数量
    """
    
    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="相关文章推荐",
            slug="related-posts",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_related_posts': True,
            'default_limit': 5,
            'recommendation_method': 'mixed',  # category, tags, mixed
            'min_common_tags': 1,  # 最少共同标签数
        }

    def register_hooks(self):
        """注册钩子"""
        # 在文章数据中附加相关文章
        if self.settings.get('enable_related_posts'):
            plugin_hooks.add_filter(
                "article_data",
                self.attach_related_posts,
                priority=10
            )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[RelatedPosts] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[RelatedPosts] Plugin deactivated")

    def attach_related_posts(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为文章附加相关推荐
        
        Args:
            article_data: 文章数据
            
        Returns:
            包含相关文章的文章数据
        """
        if not self.settings.get('enable_related_posts'):
            return article_data

        article_id = article_data.get('id') or article_data.get('article_id')
        if not article_id:
            return article_data

        # 这里可以调用异步方法获取相关文章
        # 由于钩子是同步的，我们返回一个占位符，前端可以异步加载
        article_data['related_posts_loading'] = True
        article_data['related_posts_config'] = {
            'limit': self.settings.get('default_limit', 5),
            'method': self.settings.get('recommendation_method', 'mixed'),
        }

        return article_data
    
    async def get_related_posts(
        self,
            db,
        article_id: int,
        limit: int = 5,
        method: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        获取相关文章（异步方法，供 API 调用）
        
        Args:
            db: 数据库会话
            article_id: 当前文章ID
            limit: 推荐数量
            method: 推荐方法 (category, tags, mixed)
            
        Returns:
            相关文章列表
        """
        from shared.models.article import Article
        from sqlalchemy import select
        
        try:
            # 获取当前文章
            stmt = select(Article).where(Article.id == article_id)
            result = await db.execute(stmt)
            current_article = result.scalar_one_or_none()
            
            if not current_article:
                return []
            
            related_articles = []
            
            if method in ["category", "mixed"]:
                # 基于分类推荐
                category_articles = await self._get_by_category(
                    db, current_article, limit
                )
                related_articles.extend(category_articles)
            
            if method in ["tags", "mixed"]:
                # 基于标签推荐
                tag_articles = await self._get_by_tags(
                    db, current_article, limit
                )
                # 去重
                existing_ids = {a['id'] for a in related_articles}
                for article in tag_articles:
                    if article['id'] not in existing_ids:
                        related_articles.append(article)
            
            # 限制数量
            return related_articles[:limit]
            
        except Exception as e:
            print(f"[RelatedPosts] Failed to get related posts: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_by_category(
        self,
        db: AsyncSession,
        current_article: Any,
        limit: int
    ) -> List[Dict[str, Any]]:
        """基于分类获取相关文章"""
        from shared.models.article import Article
        from sqlalchemy import desc
        
        if not current_article.category:
            return []
        
        stmt = (
            select(Article)
            .where(Article.category == current_article.category)
            .where(Article.id != current_article.id)
            .where(Article.status == 1)  # published
            .order_by(desc(Article.created_at))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        articles = result.scalars().all()
        
        return [self._article_to_dict(a) for a in articles]
    
    async def _get_by_tags(
        self,
        db: AsyncSession,
        current_article: Any,
        limit: int
    ) -> List[Dict[str, Any]]:
        """基于标签获取相关文章"""
        from shared.models.article import Article
        from sqlalchemy import desc

        if not current_article.tags_list:  # 修复：使用 tags_list
            return []
        
        # 解析标签
        current_tags = []
        if isinstance(current_article.tags_list, str):  # 修复：使用 tags_list
            current_tags = [t.strip() for t in current_article.tags_list.split(',') if t.strip()]
        elif isinstance(current_article.tags_list, list):  # 修复：使用 tags_list
            current_tags = current_article.tags_list
        
        if not current_tags:
            return []
        
        # 查找包含相同标签的文章
        stmt = (
            select(Article)
            .where(Article.id != current_article.id)
            .where(Article.status == 1)
            .order_by(desc(Article.created_at))
        )
        
        result = await db.execute(stmt)
        all_articles = result.scalars().all()
        
        # 计算标签匹配度
        scored_articles = []
        for article in all_articles:
            if not article.tags_list:  # 修复：使用 tags_list
                continue
            
            article_tags = []
            if isinstance(article.tags_list, str):  # 修复：使用 tags_list
                article_tags = [t.strip() for t in article.tags_list.split(',') if t.strip()]
            elif isinstance(article.tags_list, list):  # 修复：使用 tags_list
                article_tags = article.tags_list
            
            # 计算共同标签数
            common_tags = set(current_tags) & set(article_tags)
            if common_tags:
                score = len(common_tags)
                scored_articles.append((score, article))
        
        # 按分数排序
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        
        return [self._article_to_dict(a) for _, a in scored_articles[:limit]]
    
    def _article_to_dict(self, article: Any) -> Dict[str, Any]:
        """将文章对象转换为字典"""
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt[:100] + '...' if article.excerpt and len(article.excerpt) > 100 else article.excerpt,
            "cover_image": article.cover_image,
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(article.created_at),
            "views": article.views or 0
        }


# 全局实例
related_posts_plugin = RelatedPostsPlugin()
