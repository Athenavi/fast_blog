"""
文章搜索优化服务

功能：
1. 全文搜索（标题、内容、摘要）
2. 搜索结果高亮
3. 高级过滤（分类、标签、日期、作者）
4. 搜索建议（自动完成）
5. 搜索历史
6. 热门搜索统计
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.models.search import SearchHistory

# 状态字符串 -> Article.status 整数值
STATUS_MAP = {"published": 1, "draft": 0, "deleted": -1}


class ArticleSearchService:
    """
    文章搜索优化服务

    提供高性能的全文搜索、高亮、过滤等功能
    """

    async def search_articles(
            self,
            db: AsyncSession,
            query: str,
            category_id: Optional[int] = None,
            author_id: Optional[int] = None,
            date_from: Optional[datetime] = None,
            date_to: Optional[datetime] = None,
            status: str = "published",
            page: int = 1,
            per_page: int = 20,
            sort_by: str = "relevance"
    ) -> Dict:
        """
        搜索文章

        Args:
            db: 数据库会话
            query: 搜索关键词
            category_id: 分类ID过滤
            author_id: 作者ID过滤
            date_from: 起始日期
            date_to: 结束日期
            status: 文章状态
            page: 页码
            per_page: 每页数量
            sort_by: 排序方式 (relevance, date, views)

        Returns:
            搜索结果和分页信息
        """
        # 构建基础查询（ArticleContent.article 为外键列名；status 为 Integer）
        stmt = (
            select(Article)
            .join(ArticleContent, Article.id == ArticleContent.article, isouter=True)
            .where(Article.status == STATUS_MAP.get(status, 1))
        )

        # 全文搜索条件
        if query:
            search_conditions = [
                Article.title.ilike(f"%{query}%"),
                Article.excerpt.ilike(f"%{query}%"),
            ]

            # 如果有关联内容，也搜索内容
            search_conditions.append(
                ArticleContent.content.ilike(f"%{query}%")
            )

            stmt = stmt.where(or_(*search_conditions))

        # 分类过滤
        if category_id:
            stmt = stmt.where(Article.category == category_id)

        # 作者过滤
        if author_id:
            stmt = stmt.where(Article.user == author_id)

        # 日期范围过滤
        if date_from:
            stmt = stmt.where(Article.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Article.created_at <= date_to)

        # 排序
        if sort_by == "date":
            stmt = stmt.order_by(desc(Article.created_at))
        elif sort_by == "views":
            stmt = stmt.order_by(desc(Article.views))
        else:  # relevance - 默认按相关性（这里简化为按创建时间）
            stmt = stmt.order_by(desc(Article.created_at))

        # 获取总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()

        # 分页
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        result = await db.execute(stmt)
        articles = result.scalars().all()

        # 高亮搜索结果
        highlighted_articles = []
        for article in articles:
            article_dict = article.to_dict()

            # 添加高亮字段
            if query:
                article_dict['highlighted_title'] = self._highlight_text(
                    article.title, query
                )
                article_dict['highlighted_excerpt'] = self._highlight_text(
                    article.excerpt or "", query
                )
            else:
                article_dict['highlighted_title'] = article.title
                article_dict['highlighted_excerpt'] = article.excerpt

            highlighted_articles.append(article_dict)

        # 记录搜索历史
        if query:
            await self.record_search_history(db, query)

        return {
            'articles': highlighted_articles,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'query': query,
        }

    def _highlight_text(self, text: str, query: str, max_length: int = 200) -> str:
        """
        高亮文本中的搜索关键词（返回已 HTML 转义的安全片段）

        先对原文与关键词做 HTML 转义再插入 <mark> 高亮，防止标题/摘要
        中的恶意 HTML 被前端 dangerouslySetInnerHTML 直接执行（反射型 XSS）。
        """
        from html import escape

        if not text:
            return ""
        safe_text = escape(str(text))
        if not query:
            return safe_text[:max_length] + ("..." if len(safe_text) > max_length else "")

        safe_query = escape(query)
        pos = safe_text.lower().find(safe_query.lower())
        if pos == -1:
            return safe_text[:max_length] + ("..." if len(safe_text) > max_length else "")

        # 截取上下文
        start = max(0, pos - 50)
        end = min(len(safe_text), pos + len(safe_query) + 150)
        snippet = safe_text[start:end]

        # 添加省略号
        if start > 0:
            snippet = "..." + snippet
        if end < len(safe_text):
            snippet = snippet + "..."

        # 高亮关键词（使用 HTML 标签，关键词本身已转义）
        highlighted = snippet.replace(
            safe_query,
            f"<mark>{safe_query}</mark>",
            1  # 只替换第一个
        )

        return highlighted

    async def get_search_suggestions(
            self,
            db: AsyncSession,
            query: str,
            limit: int = 5
    ) -> List[str]:
        """
        获取搜索建议（自动完成）

        Args:
            db: 数据库会话
            query: 搜索前缀
            limit: 返回数量

        Returns:
            搜索建议列表
        """
        # 从热门文章标题中获取建议
        stmt = (
            select(Article.title)
            .where(
                Article.status == 1,
                Article.title.ilike(f"{query}%")
            )
            .order_by(desc(Article.views))
            .limit(limit)
        )

        result = await db.execute(stmt)
        titles = result.scalars().all()

        return list(titles)

    async def record_search_history(
            self,
            db: AsyncSession,
            query: str,
            user_id: Optional[int] = None
    ):
        """
        记录搜索历史

        Args:
            db: 数据库会话
            query: 搜索关键词
            user_id: 用户ID（可选）
        """
        # 检查是否已存在相同的搜索记录（最近1小时内）
        one_hour_ago = datetime.now() - timedelta(hours=1)

        stmt = select(SearchHistory).where(
            SearchHistory.keyword == query,
            SearchHistory.created_at >= one_hour_ago
        )

        if user_id:
            stmt = stmt.where(SearchHistory.user == user_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新计数
            existing.results_count = (existing.results_count or 0) + 1
        else:
            # 创建新记录
            history = SearchHistory(
                keyword=query,
                user=user_id,
                results_count=1,
                created_at=datetime.now()
            )
            db.add(history)

        await db.commit()

    async def get_popular_searches(
            self,
            db: AsyncSession,
            days: int = 7,
            limit: int = 10
    ) -> List[Dict]:
        """
        获取热门搜索

        Args:
            db: 数据库会话
            days: 统计天数
            limit: 返回数量

        Returns:
            热门搜索列表
        """
        since = datetime.now() - timedelta(days=days)

        stmt = (
            select(
                SearchHistory.keyword,
                func.sum(SearchHistory.results_count).label('total_count')
            )
            .where(SearchHistory.created_at >= since)
            .group_by(SearchHistory.keyword)
            .order_by(desc('total_count'))
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        return [
            {'query': row.keyword, 'count': row.total_count}
            for row in rows
        ]

    async def clear_old_search_history(
            self,
            db: AsyncSession,
            days: int = 30
    ):
        """
        清理旧的搜索历史

        Args:
            db: 数据库会话
            days: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(SearchHistory)
            .where(SearchHistory.updated_at < cutoff_date)
        )

        result = await db.execute(stmt)
        old_records = result.scalars().all()

        for record in old_records:
            await db.delete(record)

        await db.commit()


# 全局实例
article_search_service = ArticleSearchService()
