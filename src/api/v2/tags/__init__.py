"""
标签建议 API - V2 原生实现
为前端提供标签自动补全功能
"""
import logging

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from shared.models.article import Article
from src.extensions import cache
from src.utils.database.main import get_async_session_context
from src.utils.filters import f2list

logger = logging.getLogger('tags')

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["tags"])

    @router.get('/suggest')
    async def suggest_tags(query: str = Query("", alias="q")):
        """根据前缀建议标签（最多 5 个），缓存 10 分钟"""
        # 先尝试从缓存获取
        unique_tags = cache.get('unique_tags')
        if unique_tags is None:
            unique_tags = await _load_unique_tags()
            # 回填缓存
            cache.set('unique_tags', unique_tags, ttl=600)
        return [tag for tag in unique_tags if tag.startswith(query)][:5]

    _router = router
    return _router


async def _load_unique_tags():
    """从数据库加载去重后的标签列表（仅缓存未命中时执行）"""
    logger.info("标签缓存未命中，重新加载...")
    async with get_async_session_context() as db:
        result = await db.execute(
            select(Article.tags_list).where(
                Article.tags_list.isnot(None),
                Article.tags_list != ''
            )
        )
        rows = result.scalars().all()

    all_tags = []
    for tag_string in rows:
        if tag_string:
            all_tags.extend(f2list(tag_string.strip()))

    unique_tags = sorted(set(all_tags))
    logger.info(f"标签加载完成: {len(unique_tags)} 个唯一标签")
    return unique_tags


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
