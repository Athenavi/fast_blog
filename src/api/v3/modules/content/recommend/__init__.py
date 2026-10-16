"""content/recommend：推荐（相关文章 / 热门 / 个性化 / 标签建议）

全部基于真表（``articles`` / ``article_likes`` / ``page_views``）实时计算，
不引入进程内画像缓存 —— v2 的画像存在内存里，重启即丢且多进程不一致。
"""

from src.api.v3.modules.content.recommend.service import recommend_service

__all__ = ["recommend_service"]
