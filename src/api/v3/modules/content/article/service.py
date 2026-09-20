"""article 模块业务逻辑

正文在 ``article_content``（按 ``language_code`` 一行一语言），SEO 在 ``article_seo``；
所有写操作后都会失效文章公开缓存。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from src.api.v3.common.tags import normalize_tags
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.scope import ensure_object_in_scope
from src.api.v3.modules.content.article.crud import article_crud
from src.api.v3.modules.content.article.schema import (
    STATUS_DELETED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    ArticleCreate,
    ArticleUpdate,
)

logger = get_logger("article")

DEFAULT_LANGUAGE = "zh-CN"


def to_out(article: Article) -> dict:
    """文章主体 → 响应字典（不含正文）"""
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": article.excerpt,
        "cover_image": article.cover_image,
        "category_id": article.category,
        "tags": normalize_tags(article.tags_list),
        "views": article.views or 0,
        "likes": article.likes or 0,
        "user_id": article.user,
        "status": article.status,
        "hidden": bool(article.hidden),
        "is_featured": bool(article.is_featured),
        "is_sticky": bool(article.is_sticky),
        "is_vip_only": bool(article.is_vip_only),
        "required_vip_level": article.required_vip_level or 0,
        "post_type": article.post_type,
        "sort_order": article.sort_order or 0,
        "scheduled_publish_at": article.scheduled_publish_at,
        "published_at": article.published_at,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


class ArticleService:
    """文章管理 + 公开读"""

    # ------------------------------------------------------------------ 内部
    async def _content_row(
        self, db: AsyncSession, article_id: int, language_code: Optional[str] = None
    ) -> Optional[ArticleContent]:
        stmt = select(ArticleContent).where(ArticleContent.article == article_id)
        if language_code:
            stmt = stmt.where(ArticleContent.language_code == language_code)
        stmt = stmt.order_by(ArticleContent.id.asc())
        return (await db.execute(stmt)).scalars().first()

    async def _seo_dict(self, db: AsyncSession, article_id: int) -> Optional[dict]:
        row = (
            await db.execute(select(ArticleSEO).where(ArticleSEO.article_id == article_id))
        ).scalars().first()
        return row.to_dict() if row is not None else None

    async def _upsert_content(
        self,
        db: AsyncSession,
        article_id: int,
        content: Optional[str],
        language_code: Optional[str],
    ) -> None:
        language = language_code or DEFAULT_LANGUAGE
        now = datetime.now()
        row = await self._content_row(db, article_id, language)
        if row is None:
            db.add(
                ArticleContent(
                    article=article_id,
                    content=content or "",
                    language_code=language,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.content = content or ""
            row.updated_at = now
            db.add(row)

    @staticmethod
    def _validate_status(status: Optional[int]) -> None:
        if status is None:
            return
        if status not in (STATUS_DRAFT, STATUS_PUBLISHED):
            raise BadRequestError("status 只能是 0（草稿）或 1（已发布）")

    @staticmethod
    async def _invalidate(article_id: Optional[int] = None) -> None:
        """失效文章公开缓存（失败只记录，不影响数据写入）"""
        try:
            from shared.services.core.article_cache_service import article_cache_service

            if article_id is not None:
                await article_cache_service.invalidate_article(article_id)
            await article_cache_service.invalidate_public_caches()
        except Exception:  # noqa: BLE001
            logger.exception("文章缓存失效失败 article_id=%s", article_id)

    # ------------------------------------------------------------------ 管理端读
    async def list_articles(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        post_type: Optional[str] = None,
        is_featured: Optional[bool] = None,
        is_sticky: Optional[bool] = None,
        order_by: Optional[str] = None,
        order: str = "desc",
        scope_user: Any = None,
    ) -> Tuple[List[dict], int]:
        items, total = await article_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={
                "status": status,
                "category": category_id,
                "user": user_id,
                "post_type": post_type,
                "is_featured": is_featured,
                "is_sticky": is_sticky,
            },
            order_by=order_by or "id",
            order=order,
            scope_user=scope_user,
        )
        return [to_out(article) for article in items], total

    async def get_article(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        with_content: bool = True,
        language_code: Optional[str] = None,
        scope_user: Any = None,
    ) -> dict:
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        if scope_user is not None:
            await ensure_object_in_scope(db, Article, article, user=scope_user)

        data = to_out(article)
        if with_content:
            row = await self._content_row(db, article_id, language_code)
            data["content"] = row.content if row is not None else None
            data["language_code"] = row.language_code if row is not None else None
        data["seo"] = await self._seo_dict(db, article_id)
        return data

    # ------------------------------------------------------------------ 管理端写
    async def create_article(
        self, db: AsyncSession, payload: ArticleCreate, *, user_id: Optional[int] = None
    ) -> dict:
        self._validate_status(payload.status)
        if payload.slug and await article_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"文章 slug {payload.slug} 已存在")

        now = datetime.now()
        data = payload.model_dump(exclude={"content", "tags", "language_code", "category_id"})
        data.update(
            {
                "category": payload.category_id,
                "user": user_id,
                "tags_list": normalize_tags(payload.tags),
                "created_at": now,
                "updated_at": now,
            }
        )
        if payload.status == STATUS_PUBLISHED:
            data["published_at"] = now

        article = await article_crud.create(db, data)
        if payload.content is not None:
            await self._upsert_content(db, article.id, payload.content, payload.language_code)
            await db.commit()

        await self._invalidate(article.id)
        return await self.get_article(db, article.id)

    async def update_article(
        self, db: AsyncSession, article_id: int, payload: ArticleUpdate
    ) -> dict:
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        fields_set = payload.model_fields_set
        self._validate_status(payload.status if "status" in fields_set else None)

        data = payload.model_dump(
            exclude_unset=True, exclude={"content", "tags", "language_code", "category_id"}
        )
        if "category_id" in fields_set:
            data["category"] = payload.category_id
        if "tags" in fields_set and payload.tags is not None:
            data["tags_list"] = normalize_tags(payload.tags)
        if data.get("status") == STATUS_PUBLISHED and article.published_at is None:
            data["published_at"] = datetime.now()
        data["updated_at"] = datetime.now()

        article = await article_crud.update(db, article, data)
        if payload.content is not None:
            await self._upsert_content(
                db, article_id, payload.content, payload.language_code or DEFAULT_LANGUAGE
            )
            await db.commit()

        await self._invalidate(article_id)
        return await self.get_article(db, article_id)

    async def delete_article(self, db: AsyncSession, article_id: int) -> None:
        """软删除：``status = -1`` + ``deleted_at``（与 v2 语义一致）"""
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        await article_crud.update(
            db, article, {"status": STATUS_DELETED, "deleted_at": datetime.now()}
        )
        await self._invalidate(article_id)

    async def batch_delete(self, db: AsyncSession, ids: Sequence[int]) -> int:
        count = 0
        for article_id in ids:
            try:
                await self.delete_article(db, article_id)
                count += 1
            except NotFoundError:
                continue
        return count

    async def set_published(self, db: AsyncSession, article_id: int, publish: bool) -> dict:
        """发布 / 撤回（撤回清空 published_at，发布则补齐）"""
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        if publish:
            data: Dict[str, Any] = {
                "status": STATUS_PUBLISHED,
                "published_at": article.published_at or datetime.now(),
                "scheduled_publish_at": None,
            }
        else:
            data = {"status": STATUS_DRAFT, "published_at": None}

        article = await article_crud.update(db, article, data)
        await self._invalidate(article_id)
        return to_out(article)

    async def reorder(self, db: AsyncSession, items: Sequence[Tuple[int, int]]) -> int:
        """批量重排（id, sort_order）"""
        count = 0
        for article_id, sort_order in items:
            article = await article_crud.get(db, article_id)
            if article is None:
                continue
            await article_crud.update(db, article, {"sort_order": sort_order})
            count += 1
        if count:
            await self._invalidate()
        return count

    # ------------------------------------------------------------------ 公开读
    def _published_stmt(self):
        now = datetime.now()
        return select(Article).where(
            Article.status == STATUS_PUBLISHED,
            Article.hidden.is_(False),
            or_(
                Article.scheduled_publish_at.is_(None),
                Article.scheduled_publish_at <= now,
            ),
        )

    async def public_list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        post_type: Optional[str] = None,
        user_id: Optional[int] = None,
        user_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[List[dict], int]:
        stmt = self._published_stmt()
        if category_id is not None:
            stmt = stmt.where(Article.category == category_id)
        if post_type:
            stmt = stmt.where(Article.post_type == post_type)
        if user_id is not None:
            stmt = stmt.where(Article.user == user_id)
        if user_ids is not None:
            # 空集合 → `IN ()` 语义即"没有文章"（关注流为空时的正确结果，不是全量）
            stmt = stmt.where(Article.user.in_(list(user_ids)))
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(Article.title.ilike(like), Article.excerpt.ilike(like)))
        if tag:
            stmt = stmt.where(cast(Article.tags_list, Text).ilike(f'%"{tag}"%'))

        total = int(
            (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        )
        stmt = stmt.order_by(
            Article.is_sticky.desc(),
            Article.sort_order.asc(),
            func.coalesce(Article.published_at, Article.created_at).desc(),
            Article.id.desc(),
        )
        if page_size > 0:
            stmt = stmt.offset(max(page - 1, 0) * page_size).limit(page_size)

        articles = list((await db.execute(stmt)).scalars().all())
        return [to_out(article) for article in articles], total

    async def public_detail(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        language_code: Optional[str] = None,
        viewer: Optional[Any] = None,
    ) -> dict:
        article = await article_crud.get(db, article_id)
        if (
            article is None
            or article.status != STATUS_PUBLISHED
            or article.hidden
            or (article.scheduled_publish_at and article.scheduled_publish_at > datetime.now())
        ):
            raise NotFoundError("文章不存在或未发布")
        data = await self.get_article(db, article_id, language_code=language_code)
        return await self.apply_vip_gate(db, data, viewer)

    async def public_detail_by_slug(
        self,
        db: AsyncSession,
        slug: str,
        *,
        language_code: Optional[str] = None,
        viewer: Optional[Any] = None,
    ) -> dict:
        article = await article_crud.get_by(db, slug=slug)
        if (
            article is None
            or article.status != STATUS_PUBLISHED
            or article.hidden
            or (article.scheduled_publish_at and article.scheduled_publish_at > datetime.now())
        ):
            raise NotFoundError("文章不存在或未发布")
        data = await self.get_article(db, article.id, language_code=language_code)
        return await self.apply_vip_gate(db, data, viewer)

    async def apply_vip_gate(self, db: AsyncSession, data: dict, viewer: Optional[Any]) -> dict:
        """VIP 内容闸门：**未授权者拿不到正文**（只给摘要 + ``locked`` 标记）

        规则（``is_vip_only`` 为真时）：

          - 作者本人：始终可读（否则作者无法预览自己的付费文章）；
          - 登录且 VIP 等级 >= ``required_vip_level``（最低按 1 算）：可读；
          - 其余（含匿名 / SSR 首屏）：``content`` 置空、``locked = True``，
            但**保留摘要与元信息**（SEO 与"引导开通 VIP"都靠它）。

        正文由 ``GET /api/v3/mobile/article/{article_id}/content`` 在授权后单独下发。
        """
        data.setdefault("locked", False)
        if not data.get("is_vip_only"):
            return data

        # `is_vip_only=True` 但等级留 0 表示"任何 VIP 等级即可"，对外统一成 1
        required = max(int(data.get("required_vip_level") or 0), 1)
        data["required_vip_level"] = required

        if viewer is not None and getattr(viewer, "id", None) == data.get("user_id"):
            return data

        allowed = False
        if viewer is not None:
            from shared.services.core.membership import create_membership_service

            verdict = await create_membership_service(db).check_content_access(
                viewer.id, int(data.get("id") or 0), required
            )
            allowed = bool(verdict.get("has_access"))

        if not allowed:
            data["content"] = None
            data["locked"] = True
        return data

    async def increment_views(self, db: AsyncSession, article_id: int) -> int:
        """浏览量 +1，返回新值（前台调用，无需登录）"""
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        views = int(article.views or 0) + 1
        await article_crud.update(db, article, {"views": views})
        return views


article_service = ArticleService()
