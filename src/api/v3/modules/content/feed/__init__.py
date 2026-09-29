"""content/feed：动态流（关注时间线 / 发现流 / 用户公开动态）

事件从 ``articles`` / ``article_likes`` / ``comments`` 真表用 ``UNION ALL`` 聚合，
在库内排序分页；关注关系复用 ``mobile/follow`` 的 ``user_follows`` 真表。
"""

from src.api.v3.modules.content.feed.service import EVENT_TYPES, feed_service

__all__ = ["EVENT_TYPES", "feed_service"]
