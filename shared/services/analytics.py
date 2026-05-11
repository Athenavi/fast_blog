"""
数据分析服务

功能：
1. 访问统计
2. 文章分析
3. 用户行为
4. 趋势分析
5. 数据可视化支持
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    """
    数据分析服务
    
    参考 Google Analytics 和 Matomo 的设计模式
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_stats(self, days: int = 30) -> Dict:
        """
        获取概览统计数据
        
        Args:
            days: 统计天数
            
        Returns:
            概览数据
        """
        from shared.models.article import Article
        from shared.models.comment import Comment
        from shared.models.user import User

        cutoff_date = datetime.now() - timedelta(days=days)

        # 总文章数
        total_articles = await self.db.execute(
            func.count(Article.id)
        )

        # 新增文章数
        new_articles = await self.db.execute(
            func.count(Article.id).filter(
                Article.created_at >= cutoff_date
            )
        )

        # 总评论数
        total_comments = await self.db.execute(
            func.count(Comment.id)
        )

        # 新增评论数
        new_comments = await self.db.execute(
            func.count(Comment.id).filter(
                Comment.created_at >= cutoff_date
            )
        )

        # 总用户数
        total_users = await self.db.execute(
            func.count(User.id)
        )

        # 新增用户数
        new_users = await self.db.execute(
            func.count(User.id).filter(
                User.created_at >= cutoff_date
            )
        )

        return {
            'total_articles': total_articles.scalar(),
            'new_articles': new_articles.scalar(),
            'total_comments': total_comments.scalar(),
            'new_comments': new_comments.scalar(),
            'total_users': total_users.scalar(),
            'new_users': new_users.scalar(),
            'period_days': days,
        }

    async def get_article_views_trend(self, days: int = 30) -> List[Dict]:
        """
        获取文章浏览量趋势
        
        Args:
            days: 统计天数
            
        Returns:
            每日浏览量列表
        """
        from shared.models.article_view import ArticleView

        cutoff_date = datetime.now() - timedelta(days=days)

        # 按日期分组统计
        result = await self.db.execute(
            func.date(ArticleView.viewed_at).label('date'),
            func.count(ArticleView.id).label('views')
        ).filter(
            ArticleView.viewed_at >= cutoff_date
        ).group_by(
            func.date(ArticleView.viewed_at)
        ).order_by(
            func.date(ArticleView.viewed_at)
        )

        trend_data = []
        for row in result.all():
            trend_data.append({
                'date': str(row.date),
                'views': row.views,
            })

        return trend_data

    async def get_popular_articles(self, limit: int = 10, days: int = 7) -> List[Dict]:
        """
        获取热门文章
        
        Args:
            limit: 返回数量
            days: 统计天数
            
        Returns:
            热门文章列表
        """
        from shared.models.article import Article
        from shared.models.article_view import ArticleView

        cutoff_date = datetime.now() - timedelta(days=days)

        # 统计每篇文章的浏览量
        result = await self.db.execute(
            Article.id,
            Article.title,
            Article.slug,
            func.count(ArticleView.id).label('view_count')
        ).join(
            ArticleView, Article.id == ArticleView.article_id
        ).filter(
            ArticleView.viewed_at >= cutoff_date
        ).group_by(
            Article.id, Article.title, Article.slug
        ).order_by(
            func.count(ArticleView.id).desc()
        ).limit(limit)

        popular_articles = []
        for row in result.all():
            popular_articles.append({
                'id': row.id,
                'title': row.title,
                'slug': row.slug,
                'view_count': row.view_count,
            })

        return popular_articles

    async def get_category_distribution(self) -> List[Dict]:
        """
        获取分类分布
        
        Returns:
            分类统计列表
        """
        from shared.models.article import Article
        from shared.models.category import Category

        result = await self.db.execute(
            Category.name,
            func.count(Article.id).label('article_count')
        ).join(
            Article, Article.category_id == Category.id
        ).group_by(
            Category.name
        ).order_by(
            func.count(Article.id).desc()
        )

        distribution = []
        for row in result.all():
            distribution.append({
                'category': row.name,
                'count': row.article_count,
            })

        return distribution

    async def get_user_activity(self, days: int = 30) -> Dict:
        """
        获取用户活动统计
        
        Args:
            days: 统计天数
            
        Returns:
            用户活动数据
        """
        from shared.models.article import Article
        from shared.models.comment import Comment
        from shared.models.user import User

        cutoff_date = datetime.now() - timedelta(days=days)

        # 活跃作者（发布过文章的用户）
        active_authors = await self.db.execute(
            func.count(func.distinct(Article.author_id))
        ).filter(
            Article.created_at >= cutoff_date
        )

        # 活跃评论者
        active_commenters = await self.db.execute(
            func.count(func.distinct(Comment.user_id))
        ).filter(
            Comment.created_at >= cutoff_date
        )

        # 新用户
        new_users = await self.db.execute(
            func.count(User.id)
        ).filter(
            User.created_at >= cutoff_date
        )

        return {
            'active_authors': active_authors.scalar(),
            'active_commenters': active_commenters.scalar(),
            'new_users': new_users.scalar(),
            'period_days': days,
        }

    async def get_content_performance(self, days: int = 30) -> Dict:
        """
        获取内容表现分析
        
        Args:
            days: 统计天数
            
        Returns:
            内容表现数据
        """
        from shared.models.article import Article
        from shared.models.article_view import ArticleView
        from shared.models.comment import Comment

        cutoff_date = datetime.now() - timedelta(days=days)

        # 平均浏览量
        avg_views = await self.db.execute(
            func.avg(
                func.count(ArticleView.id)
            )
        ).join(
            ArticleView, Article.id == ArticleView.article_id, isouter=True
        ).filter(
            Article.created_at >= cutoff_date
        ).group_by(
            Article.id
        )

        # 平均评论数
        avg_comments = await self.db.execute(
            func.avg(
                func.count(Comment.id)
            )
        ).join(
            Comment, Article.id == Comment.article_id, isouter=True
        ).filter(
            Article.created_at >= cutoff_date
        ).group_by(
            Article.id
        )

        return {
            'avg_views_per_article': round(avg_views.scalar() or 0, 2),
            'avg_comments_per_article': round(avg_comments.scalar() or 0, 2),
            'period_days': days,
        }

    async def get_traffic_sources(self, days: int = 30) -> List[Dict]:
        """
        获取流量来源分析
        
        Args:
            days: 统计天数
            
        Returns:
            流量来源列表
        """
        from shared.models.article_view import ArticleView

        cutoff_date = datetime.now() - timedelta(days=days)

        # 按引荐来源分组
        result = await self.db.execute(
            ArticleView.referrer,
            func.count(ArticleView.id).label('count')
        ).filter(
            ArticleView.viewed_at >= cutoff_date,
            ArticleView.referrer.isnot(None)
        ).group_by(
            ArticleView.referrer
        ).order_by(
            func.count(ArticleView.id).desc()
        ).limit(10)

        sources = []
        for row in result.all():
            sources.append({
                'source': row.referrer or 'Direct',
                'count': row.count,
            })

        return sources

    async def get_device_stats(self, days: int = 30) -> Dict:
        """
        获取设备统计
        
        Args:
            days: 统计天数
            
        Returns:
            设备分布数据
        """
        from shared.models.article_view import ArticleView

        cutoff_date = datetime.now() - timedelta(days=days)

        # 按设备类型分组
        result = await self.db.execute(
            ArticleView.device_type,
            func.count(ArticleView.id).label('count')
        ).filter(
            ArticleView.viewed_at >= cutoff_date
        ).group_by(
            ArticleView.device_type
        )

        devices = {}
        total = 0

        for row in result.all():
            device = row.device_type or 'unknown'
            count = row.count
            devices[device] = count
            total += count

        # 计算百分比
        device_stats = {}
        for device, count in devices.items():
            percentage = round((count / total * 100) if total > 0 else 0, 2)
            device_stats[device] = {
                'count': count,
                'percentage': percentage,
            }

        return device_stats


# 工厂函数
def create_analytics_service(db: AsyncSession) -> AnalyticsService:
    return AnalyticsService(db)
