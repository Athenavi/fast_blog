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
from src.api.v3.core.permission import codes as C
from src.api.v3.core.permission.scope import ensure_object_in_scope, ensure_write_in_scope
from src.api.v3.modules.content.approval.guard import (
    ARTICLE_CONTENT_TYPE,
    ensure_batch_publish_allowed,
    ensure_new_content_publish_allowed,
    ensure_publish_allowed,
)
from src.api.v3.modules.content.article.crud import article_crud
from src.api.v3.modules.content.article.locale import (
    pick_locale,
    resolve_requested_locale,
)
from src.api.v3.modules.content.article.schema import (
    STATUS_DELETED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    ArticleCreate,
    ArticleUpdate,
)

logger = get_logger("article")

DEFAULT_LANGUAGE = "zh-CN"


async def _assert_article_write(
    db: AsyncSession, article: Article, *, scope_user: Any, others_code: str
) -> None:
    """管理端写路径校验：数据范围 + 他人数据权限（``scope_user`` 为空 = 内部调用，跳过）"""
    if scope_user is not None:
        await ensure_write_in_scope(
            db, Article, article, user=scope_user, others_code=others_code
        )


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

    async def _content_row_by_chain(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        locale: Optional[str] = None,
        accept_language: Optional[str] = None,
    ) -> Tuple[Optional[ArticleContent], Optional[str]]:
        """按 locale 回退链取正文行，返回 ``(行, 实际命中的语言)``。

        与 ``_content_row``（精确匹配、否则首行）的区别：指定语言缺失时不直接给空，
        而是按链回退（``zh-CN`` → ``zh`` → 默认语言）；链完全不命中时退到该文章
        已有的第一条语言，并把**实际语言**回传，供响应里的 ``resolved_locale`` 使用。
        """
        rows = (
            await db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
            )
        ).scalars().all()
        if not rows:
            return None, None

        available = [getattr(row, "language_code", None) for row in rows]
        chain = resolve_requested_locale(locale, accept_language)
        hit = pick_locale(available, chain)
        if hit is not None:
            for row in rows:
                current = str(getattr(row, "language_code", "") or "")
                if current.lower() == hit.lower():
                    return row, getattr(row, "language_code", None)
        first = rows[0]
        return first, getattr(first, "language_code", None)

    async def available_locales(self, db: AsyncSession, article_id: int) -> List[str]:
        """该文章已有正文的语言列表（按行序去重）"""
        rows = (
            await db.execute(
                select(ArticleContent.language_code)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
            )
        ).scalars().all()
        out: List[str] = []
        for item in rows:
            if item and item not in out:
                out.append(item)
        return out

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
            row, resolved = await self._content_row_by_chain(db, article_id, locale=language_code)
            data["content"] = row.content if row is not None else None
            data["language_code"] = row.language_code if row is not None else None
            # 实际命中的语言：与请求语言不同即说明"发生了回退"，前端可据此提示
            data["resolved_locale"] = resolved
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
            # 新建即发布也要过闸门：新内容没有 id、不可能已有审批单，
            # 因此这里只看「该类型是否被配置为先审批后发布」
            await ensure_new_content_publish_allowed(db, content_type=ARTICLE_CONTENT_TYPE)
            data["published_at"] = now

        article = await article_crud.create(db, data)
        if payload.content is not None:
            await self._upsert_content(db, article.id, payload.content, payload.language_code)
            await db.commit()

        await self._invalidate(article.id)
        return await self.get_article(db, article.id)

    async def update_article(
        self,
        db: AsyncSession,
        article_id: int,
        payload: ArticleUpdate,
        *,
        scope_user: Any = None,
    ) -> dict:
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        await _assert_article_write(
            db, article, scope_user=scope_user, others_code=C.ARTICLE_EDIT_OTHERS
        )

        fields_set = payload.model_fields_set
        self._validate_status(payload.status if "status" in fields_set else None)

        data = payload.model_dump(
            exclude_unset=True, exclude={"content", "tags", "language_code", "category_id"}
        )
        if "category_id" in fields_set:
            data["category"] = payload.category_id
        if "tags" in fields_set and payload.tags is not None:
            data["tags_list"] = normalize_tags(payload.tags)
        if "status" in fields_set and payload.status == STATUS_PUBLISHED and article.status != STATUS_PUBLISHED:
            # 与 POST /{id}/publish 走**同一个**审批闸门：否则「编辑接口改状态」就是绕过审批的后门
            await ensure_publish_allowed(
                db, content_type=ARTICLE_CONTENT_TYPE, content_id=article_id
            )
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

    async def delete_article(
        self, db: AsyncSession, article_id: int, *, scope_user: Any = None
    ) -> None:
        """软删除：``status = -1`` + ``deleted_at``（与 v2 语义一致）"""
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        await _assert_article_write(
            db, article, scope_user=scope_user, others_code=C.ARTICLE_DELETE_OTHERS
        )
        await article_crud.update(
            db, article, {"status": STATUS_DELETED, "deleted_at": datetime.now()}
        )
        await self._invalidate(article_id)

    async def _assert_batch_writable(
        self,
        db: AsyncSession,
        ids: Sequence[int],
        *,
        scope_user: Any,
        others_code: str,
    ) -> None:
        """批量写操作的前置校验：逐个核对归属 / 数据范围 / 他人数据权限"""
        if scope_user is None:
            return
        for article_id in ids:
            article = await article_crud.get(db, article_id)
            if article is not None:
                await _assert_article_write(
                    db, article, scope_user=scope_user, others_code=others_code
                )

    async def batch_delete(
        self, db: AsyncSession, ids: Sequence[int], *, scope_user: Any = None
    ) -> int:
        await self._assert_batch_writable(
            db, ids, scope_user=scope_user, others_code=C.ARTICLE_DELETE_OTHERS
        )
        count = 0
        for article_id in ids:
            try:
                await self.delete_article(db, article_id)
                count += 1
            except NotFoundError:
                continue
        return count

    async def batch_set_published(
        self, db: AsyncSession, ids: Sequence[int], publish: bool, *, scope_user: Any = None
    ) -> int:
        """批量发布 / 撤回：逐条复用 set_published，忽略不存在的 id"""
        await self._assert_batch_writable(
            db, ids, scope_user=scope_user, others_code=C.ARTICLE_EDIT_OTHERS
        )
        if publish:
            # 批量发布：**一次** IN 查询校验全部（避免 N+1），任一条被拦则整体拒绝并列出全部原因
            await ensure_batch_publish_allowed(
                db, content_type=ARTICLE_CONTENT_TYPE, ids=list(ids)
            )
        count = 0
        for article_id in ids:
            try:
                await self.set_published(db, article_id, publish)
                count += 1
            except NotFoundError:
                continue
        return count

    async def set_published(
        self, db: AsyncSession, article_id: int, publish: bool, *, scope_user: Any = None
    ) -> dict:
        """发布 / 撤回（撤回清空 published_at，发布则补齐）"""
        article = await article_crud.get(db, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        await _assert_article_write(
            db, article, scope_user=scope_user, others_code=C.ARTICLE_EDIT_OTHERS
        )

        if publish:
            # 审批闸门：待审 / 被驳回 / 该类型被配置为必须审批但尚未通过 → 拒绝（真实查 approval_records）
            await ensure_publish_allowed(
                db, content_type=ARTICLE_CONTENT_TYPE, content_id=article_id
            )
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

    async def reorder(
        self, db: AsyncSession, items: Sequence[Tuple[int, int]], *, scope_user: Any = None
    ) -> int:
        """批量重排（id, sort_order）"""
        await self._assert_batch_writable(
            db,
            [article_id for article_id, _ in items],
            scope_user=scope_user,
            others_code=C.ARTICLE_EDIT_OTHERS,
        )
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
        exclude_vip: bool = False,
    ) -> Tuple[List[dict], int]:
        stmt = self._published_stmt()
        if category_id is not None:
            stmt = stmt.where(Article.category == category_id)
        if post_type:
            stmt = stmt.where(Article.post_type == post_type)
        if user_id is not None:
            stmt = stmt.where(Article.user == user_id)
        if exclude_vip:
            # 作者主页等"对外展示清单"用：VIP 文章点进去才锁定，列表里先不露出。
            # `isnot(True)` 同时覆盖 NULL（历史行未回填）与 False。
            stmt = stmt.where(Article.is_vip_only.isnot(True))
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
