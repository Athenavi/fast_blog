"""tag 模块业务逻辑（基于 ``articles.tags_list`` JSON，不建表）

所有写操作都直接回写文章行的 JSON 字段，并失效文章公开缓存。
"""

from collections import Counter
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import Text, cast, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from src.api.v3.common.tags import normalize_tags as _normalize_names
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.tag.schema import TagOut

logger = get_logger("tag")


class TagService:
    """标签查询与维护"""

    async def _aggregate_in_python(self, db: AsyncSession) -> Counter:
        stmt = select(Article.tags_list).where(Article.status != -1)
        counter: Counter = Counter()
        for value in (await db.execute(stmt)).scalars().all():
            counter.update(_normalize_names(value))
        return counter

    async def _aggregate_in_db(self, db: AsyncSession) -> Counter:
        """用 PostgreSQL 的 json_array_elements_text 展开统计"""
        sql = text(
            """
            SELECT tag, COUNT(*) AS cnt
            FROM articles,
                 json_array_elements_text(COALESCE(tags_list, '[]'::json)) AS tag
            WHERE status <> -1
              AND tag IS NOT NULL
              AND tag <> ''
            GROUP BY tag
            """
        )
        counter: Counter = Counter()
        for tag, cnt in (await db.execute(sql)).all():
            counter[str(tag)] += int(cnt)
        return counter

    async def aggregate(self, db: AsyncSession) -> Counter:
        try:
            return await self._aggregate_in_db(db)
        except Exception as exc:  # noqa: BLE001 - 非 PostgreSQL 或 JSON 类型差异时回退
            logger.warning("数据库侧标签聚合失败，回退到 Python 聚合：%s", exc)
            return await self._aggregate_in_python(db)

    async def list_tags(
        self,
        db: AsyncSession,
        *,
        limit: int = 200,
        keyword: Optional[str] = None,
        min_count: int = 1,
    ) -> Tuple[List[dict], int]:
        counter = await self.aggregate(db)
        items = [
            TagOut(name=name, count=count)
            for name, count in counter.most_common()
            if count >= min_count and (not keyword or keyword.lower() in name.lower())
        ]
        total = len(items)
        return [item.model_dump() for item in items[:limit]], total

    async def articles_by_tag(
        self,
        db: AsyncSession,
        tag: str,
        *,
        page: int = 1,
        page_size: int = 20,
        published_only: bool = True,
    ) -> Tuple[List[Article], int]:
        """按标签查文章（JSON 内含匹配；用 ilike 兜底以兼容 JSON/文本存储差异）"""
        needle = f'%"{tag}"%'
        conditions = [cast(Article.tags_list, Text).ilike(needle)]
        if published_only:
            conditions.append(Article.status == 1)

        stmt = select(Article).where(Article.status != -1, or_(*conditions))
        count_stmt = select(Article.id).where(Article.status != -1, or_(*conditions))
        total = len(list((await db.execute(count_stmt)).scalars().all()))

        stmt = stmt.order_by(Article.created_at.desc())
        if page_size > 0:
            stmt = stmt.offset(max(page - 1, 0) * page_size).limit(page_size)
        return list((await db.execute(stmt)).scalars().all()), total

    async def _articles_with_tag(self, db: AsyncSession, tag: str) -> Sequence[Article]:
        needle = f'%"{tag}"%'
        stmt = select(Article).where(
            Article.status != -1, cast(Article.tags_list, Text).ilike(needle)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def rename_tag(self, db: AsyncSession, old_name: str, new_name: str) -> dict:
        """重命名标签；目标标签已存在时等于合并"""
        old_name, new_name = old_name.strip(), new_name.strip()
        if not old_name or not new_name:
            raise BadRequestError("标签名不能为空")
        if old_name == new_name:
            raise BadRequestError("新旧标签名相同")

        counter = await self.aggregate(db)
        merged = new_name in counter
        articles = await self._articles_with_tag(db, old_name)

        for article in articles:
            names = _normalize_names(article.tags_list)
            replaced = [new_name if name == old_name else name for name in names]
            # 合并时去重，保持顺序
            deduped: List[str] = []
            for name in replaced:
                if name not in deduped:
                    deduped.append(name)
            article.tags_list = deduped
            db.add(article)
        await db.commit()

        await self._invalidate(articles)
        return {"old_name": old_name, "new_name": new_name, "affected": len(articles), "merged": merged}

    async def delete_tag(self, db: AsyncSession, name: str) -> dict:
        """从所有文章中移除该标签"""
        target = name.strip()
        if not target:
            raise BadRequestError("标签名不能为空")

        articles = await self._articles_with_tag(db, target)
        for article in articles:
            names = [item for item in _normalize_names(article.tags_list) if item != target]
            article.tags_list = names
            db.add(article)
        await db.commit()

        await self._invalidate(articles)
        return {"name": target, "affected": len(articles)}

    @staticmethod
    async def _invalidate(articles: Sequence[Article]) -> None:
        if not articles:
            return
        try:
            from shared.services.core.article_cache_service import article_cache_service

            for article in articles:
                await article_cache_service.invalidate_article(article.id)
            await article_cache_service.invalidate_public_caches()
        except Exception:  # noqa: BLE001 - 缓存失效失败不影响数据正确性
            logger.exception("标签变更后失效文章缓存失败")


tag_service = TagService()
