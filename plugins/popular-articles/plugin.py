"""
Popular Articles Plugin
读取主数据库 Article.views，返回热门文章排行
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from shared.services.plugins.plugin_manager.core import BasePlugin
from shared.services.plugins.plugin_manager import requires_capability


class PopularArticlesPlugin(BasePlugin):
    """阅读排行插件 — 展示热门文章到侧边栏"""

    def __init__(self):
        super().__init__(
            plugin_id=3005,
            name="Popular Articles",
            slug="popular-articles",
            version="1.0.0",
        )
        self.settings = {'enabled': True, 'max_items': 5, 'days': 30, 'show_views': True}

    def activate(self):
        super().activate()

    def deactivate(self):
        super().deactivate()

    def subscribers(self) -> list:
        return []

    @requires_capability("read:popular-articles")
    def get_popular(self, max_items: int = 5, days: int = 30) -> Dict[str, Any]:
        """获取热门文章列表"""
        try:
            from sqlalchemy import select, func
            from shared.models.article import Article
            from src.utils.database.unified_manager import db_manager

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            sync_session = db_manager.get_sync_session()

            try:
                query = (
                    select(Article)
                    .where(Article.status == 1, Article.created_at >= cutoff)
                    .order_by(Article.views.desc().nullslast())
                    .limit(max_items)
                )
                result = sync_session.execute(query)
                articles = result.scalars().all()

                items = []
                for a in articles:
                    items.append({
                        "id": a.id,
                        "title": a.title,
                        "slug": a.slug,
                        "views": a.views or 0,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    })

                return {"success": True, "data": items, "total": len(items)}
            finally:
                sync_session.close()
        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
plugin = PopularArticlesPlugin()
