"""
高级数据分析服务
提供访客来源、热门文章、用户留存等深度分析
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession


class AdvancedAnalyticsService:
    """
    高级数据分析服务
    
    功能:
    1. 访客来源分析
    2. 热门文章排行
    3. 用户留存率
    4. 转化漏斗
    5. 实时在线人数估算
    6. 搜索引擎排名跟踪(基础)
    """

    async def get_visitor_sources(self, db: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """
        获取访客来源分析
        
        Args:
            db: 数据库会话
            days: 分析天数
            
        Returns:
            访客来源数据
        """
        try:
            from shared.models.page_view import PageView

            cutoff_date = datetime.now() - timedelta(days=days)

            # 查询页面访问记录
            query = (
                select(PageView)
                .where(PageView.created_at >= cutoff_date)
            )
            result = await db.execute(query)
            page_views = result.scalars().all()

            # 分析来源
            sources = {
                'direct': 0,  # 直接访问
                'search': 0,  # 搜索引擎
                'social': 0,  # 社交媒体
                'referral': 0,  # 引用链接
                'other': 0
            }

            search_engines = ['google', 'baidu', 'bing', 'yahoo', 'sogou', 'so.com']
            social_platforms = ['weibo', 'wechat', 'qq', 'facebook', 'twitter', 'linkedin']

            for pv in page_views:
                referrer = (pv.referrer or '').lower()

                if not referrer or referrer == '':
                    sources['direct'] += 1
                elif any(engine in referrer for engine in search_engines):
                    sources['search'] += 1
                elif any(platform in referrer for platform in social_platforms):
                    sources['social'] += 1
                elif 'http' in referrer:
                    sources['referral'] += 1
                else:
                    sources['other'] += 1

            total = sum(sources.values())

            return {
                'success': True,
                'data': {
                    'sources': sources,
                    'total_visits': total,
                    'percentages': {
                        k: round((v / total * 100) if total > 0 else 0, 2)
                        for k, v in sources.items()
                    }
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_popular_articles(
            self,
            db: AsyncSession,
            limit: int = 10,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        获取热门文章排行
        
        Args:
            db: 数据库会话
            limit: 返回数量
            days: 统计天数
            
        Returns:
            热门文章列表
        """
        try:
            from shared.models.article import Article

            cutoff_date = datetime.now() - timedelta(days=days)

            # 查询热门文章(按浏览量排序)
            query = (
                select(Article)
                .where(Article.status == 1)  # 已发布
                .where(Article.created_at >= cutoff_date)
                .order_by(desc(Article.views))
                .limit(limit)
            )

            result = await db.execute(query)
            articles = result.scalars().all()

            popular_articles = []
            for i, article in enumerate(articles, 1):
                popular_articles.append({
                    'rank': i,
                    'id': article.id,
                    'title': article.title,
                    'slug': article.slug,
                    'views': article.views or 0,
                    'likes': article.likes or 0,
                    'created_at': article.created_at.isoformat() if article.created_at else None,
                    'engagement_score': self._calculate_engagement_score(
                        article.views or 0,
                        article.likes or 0
                    )
                })

            return {
                'success': True,
                'data': {
                    'articles': popular_articles,
                    'period_days': days,
                    'total_analyzed': len(popular_articles)
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_user_retention_rate(
            self,
            db: AsyncSession,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        计算用户留存率
        
        Args:
            db: 数据库会话
            days: 分析周期
            
        Returns:
            留存率数据
        """
        try:
            from shared.models.user import User
            from shared.models.page_view import PageView

            cutoff_date = datetime.now() - timedelta(days=days)

            # 获取在分析周期内注册的用户
            new_users_query = (
                select(User)
                .where(User.created_at >= cutoff_date)
            )
            new_users_result = await db.execute(new_users_query)
            new_users = new_users_result.scalars().all()

            if not new_users:
                return {
                    'success': True,
                    'data': {
                        'retention_rates': {},
                        'total_new_users': 0
                    }
                }

            # 计算不同时间段的留存率
            retention_periods = [1, 7, 14, 30]  # 1天、7天、14天、30天
            retention_rates = {}

            for period in retention_periods:
                if period > days:
                    continue

                period_date = datetime.now() - timedelta(days=period)

                # 统计在该时间段后仍有活动的用户
                active_users_query = (
                    select(func.count(func.distinct(PageView.user_id)))
                    .where(PageView.user_id.in_([u.id for u in new_users]))
                    .where(PageView.created_at >= period_date)
                )
                active_result = await db.execute(active_users_query)
                active_users = active_result.scalar() or 0

                retention_rate = (active_users / len(new_users) * 100) if new_users else 0
                retention_rates[f'{period}d'] = {
                    'active_users': active_users,
                    'total_users': len(new_users),
                    'rate': round(retention_rate, 2)
                }

            return {
                'success': True,
                'data': {
                    'retention_rates': retention_rates,
                    'total_new_users': len(new_users),
                    'period_days': days
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_conversion_funnel(self, db: AsyncSession) -> Dict[str, Any]:
        """
        获取转化漏斗数据
        
        追踪用户从访问到关键行为的转化路径
        
        Returns:
            转化漏斗数据
        """
        try:
            from shared.models.user import User
            from shared.models.article import Article
            from shared.models.page_view import PageView

            # 统计各阶段用户数
            total_visitors_query = select(func.count(func.distinct(PageView.session_id)))
            total_visitors_result = await db.execute(total_visitors_query)
            total_visitors = total_visitors_result.scalar() or 0

            registered_users_query = select(func.count()).select_from(User)
            registered_result = await db.execute(registered_users_query)
            registered_users = registered_result.scalar() or 0

            # 有互动的用户(点赞或评论)
            engaged_users_query = select(func.count(func.distinct(PageView.user_id))).where(
                PageView.user_id.isnot(None)
            )
            engaged_result = await db.execute(engaged_users_query)
            engaged_users = engaged_result.scalar() or 0

            # 内容创作者
            authors_query = select(func.count(func.distinct(Article.user_id)))
            authors_result = await db.execute(authors_query)
            content_creators = authors_result.scalar() or 0

            funnel = [
                {
                    'stage': 'visitors',
                    'name': '访客',
                    'count': total_visitors,
                    'percentage': 100.0
                },
                {
                    'stage': 'registered',
                    'name': '注册用户',
                    'count': registered_users,
                    'percentage': round((registered_users / total_visitors * 100) if total_visitors > 0 else 0, 2)
                },
                {
                    'stage': 'engaged',
                    'name': '活跃用户',
                    'count': engaged_users,
                    'percentage': round((engaged_users / total_visitors * 100) if total_visitors > 0 else 0, 2)
                },
                {
                    'stage': 'creators',
                    'name': '内容创作者',
                    'count': content_creators,
                    'percentage': round((content_creators / total_visitors * 100) if total_visitors > 0 else 0, 2)
                }
            ]

            return {
                'success': True,
                'data': {
                    'funnel': funnel,
                    'total_stages': len(funnel)
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_realtime_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        获取实时统计数据(估算)
        
        Returns:
            实时统计数据
        """
        try:
            from shared.models.page_view import PageView

            # 统计最近5分钟的活动
            five_minutes_ago = datetime.now() - timedelta(minutes=5)

            recent_activity_query = (
                select(func.count(func.distinct(PageView.session_id)))
                .where(PageView.created_at >= five_minutes_ago)
            )
            activity_result = await db.execute(recent_activity_query)
            active_sessions = activity_result.scalar() or 0

            # 估算在线人数(简化算法)
            estimated_online = max(1, active_sessions // 2)

            # 今日统计
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            today_views_query = (
                select(func.count())
                .where(PageView.created_at >= today_start)
            )
            today_result = await db.execute(today_views_query)
            today_views = today_result.scalar() or 0

            return {
                'success': True,
                'data': {
                    'estimated_online_users': estimated_online,
                    'active_sessions_5min': active_sessions,
                    'today_page_views': today_views,
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _calculate_engagement_score(views: int, likes: int) -> float:
        """
        计算文章互动得分
        
        Args:
            views: 浏览量
            likes: 点赞数
            
        Returns:
            互动得分(0-100)
        """
        if views == 0:
            return 0.0

        # 点赞率权重更高
        like_rate = (likes / views) * 100
        score = min(100, like_rate * 10 + (views / 100))

        return round(score, 2)


# 全局实例
advanced_analytics = AdvancedAnalyticsService()
