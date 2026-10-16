"""搜索索引同步订阅者：把文章变更真实同步到 Meilisearch

## 为什么用事件总线，而不是在文章服务里直接调索引

`article/service.py` 的写入路径已经会发 `article.published` / `article.updated` /
`article.deleted` 三个事件。在这里订阅就能覆盖**所有**写入口（后台、开放 API、
未来新增的任何入口），而不必在每个写方法里各插一次调用 —— 漏插一处，
索引与库就不一致，而且这种不一致很难被发现。

## 为什么事件只带 id、这里回查数据库

事件载荷带的是 `article_id` 等少量字段，而索引需要 `content` / `hidden` /
`site_id` / `status` / `scheduled_publish_at`。**回查一次**比把载荷撑大更可靠：
载荷字段会随表结构漂移，而回查永远拿到当前真实值。

## 不可见的文章**不写进索引**

与其"先写进去、再靠查询侧过滤"，不如一开始就不写：索引里躺着不该被搜到的文档，
一旦某天查询侧的条件被改错（或被绕过），泄漏就立刻发生。查询侧过滤是**第二道**
防线，不是第一道。
"""

from datetime import datetime
from typing import Any

from shared.logging import default_logger as logger
from shared.models.article.article import Article
from shared.services.integrations.meilisearch_service import meilisearch_service
from shared.services.plugins.event_bus import (
    ArticleDeletedPayload,
    ArticlePublishedPayload,
    ArticleUpdatedPayload,
    event_bus,
)

#: 与 `article/service.py::_published_stmt` 一致：1 = 已发布
STATUS_PUBLISHED = 1


def _is_indexable(article: Any) -> bool:
    """是否应进索引（与前台公开读的口径逐条对齐）

    与 `article/service.py::_published_stmt` 的四个条件保持一致：
    已发布 + 未隐藏 + 定时发布时间已到（+ 站点由查询侧按上下文收窄）。
    """
    if int(getattr(article, "status", 0) or 0) != STATUS_PUBLISHED:
        return False
    if bool(getattr(article, "hidden", False)):
        return False
    scheduled = getattr(article, "scheduled_publish_at", None)
    if scheduled is not None and scheduled > datetime.now():
        return False
    return True


async def _remove(article_id: int) -> None:
    """从索引删除（失败只告警：索引是派生数据，不该影响业务写入）"""
    try:
        await meilisearch_service.delete_article(article_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("从搜索索引删除文章 %s 失败：%s", article_id, exc)


async def _sync(article_id: int) -> None:
    """按 id 回查文章并同步到索引

    取不到（已物理删除）或不再可见时，**从索引移除** —— 否则索引里会留下
    "库中已不存在/已隐藏"的文档，搜索结果就会出现点进去 404 的条目。
    """
    # 惰性 import：避免模块导入期就把数据库管理器拉起来（订阅者注册发生在启动早期）
    from src.utils.database.unified_manager import db_manager

    from src.api.v3.modules.system.search.service import _to_document

    try:
        async with db_manager.get_session() as db:
            article = await db.get(Article, article_id)
            if article is None or not _is_indexable(article):
                await _remove(article_id)
                return
            await meilisearch_service.index_article(_to_document(article))
    except Exception as exc:  # noqa: BLE001 - 索引同步失败不影响文章写入
        logger.warning("同步文章 %s 到搜索索引失败：%s", article_id, exc)


async def _on_published(payload: ArticlePublishedPayload) -> None:
    await _sync(int(payload.article_id))


async def _on_updated(payload: ArticleUpdatedPayload) -> None:
    await _sync(int(payload.article_id))


async def _on_deleted(payload: ArticleDeletedPayload) -> None:
    await _remove(int(payload.article_id))


def register_search_subscriber() -> None:
    """注册搜索索引同步订阅者（应用启动时调用一次）

    幂等：重复注册同一个函数到同一个事件上只会生效一次（EventBus 内部按
    订阅者身份去重），因此重启或重复调用都不会造成重复同步。
    """
    event_bus.listen("article.published", _on_published)
    event_bus.listen("article.updated", _on_updated)
    event_bus.listen("article.deleted", _on_deleted)
    logger.info("搜索索引同步订阅者已注册（article.published/updated/deleted）")
