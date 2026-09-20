"""mobile/article 的用户投稿逻辑

复用 ``modules/content/article`` 的 ``article_service``，在其之上加三层约束：

1. **归属**：列表只查自己的，详情/更新/删除先校验 ``article.user == current.id``，
   不符返回 404（不泄露存在性）。
2. **只能存草稿**：创建时强制 ``status = STATUS_DRAFT``；更新时**忽略**任何改状态的企图。
   发布走后台 ``/content/article/{id}/publish``，即"投稿 → 审核 → 发布"的分离。
3. **管理字段归零**：`is_featured` / `is_sticky` / `hidden` / `sort_order`
   一律由服务端设定，前台无法自助设置。
   **例外**：`is_vip_only` / `required_vip_level` 是内容属性（2026-09-20 批次 16 放开），
   作者可以把自己的稿件标为"仅 VIP 可见"并指定所需等级。

另有前台点赞（``toggle_like`` / ``like_status``）：仅认证用户可写，
per-user 表去重，不允许刷赞。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_like import ArticleLike
from src.api.v3.core.exceptions import ForbiddenError, NotFoundError
from src.api.v3.modules.content.article.crud import article_crud
from src.api.v3.modules.content.article.schema import ArticleCreate, ArticleUpdate
from src.api.v3.modules.content.article.service import (
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    article_service,
)
from src.api.v3.modules.mobile.article.schema import (
    MobileArticleCreate,
    MobileArticleUpdate,
)


class MobileArticleService:
    """前台投稿（全部以当前用户为界）"""

    # ------------------------------------------------------------ 读
    async def list_mine(
        self,
        db: AsyncSession,
        user,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        return await article_service.list_articles(
            db,
            page=page,
            page_size=page_size,
            status=status,
            keyword=keyword,
            user_id=user.id,
        )

    async def get_mine(self, db: AsyncSession, user, article_id: int) -> dict:
        await self._mine_or_404(db, user, article_id)
        return await article_service.get_article(db, article_id, with_content=True)

    # ------------------------------------------------------------ 写
    async def create_draft(self, db: AsyncSession, user, payload: MobileArticleCreate) -> dict:
        """创建草稿：管理字段一律由服务端决定"""
        return await article_service.create_article(
            db,
            ArticleCreate(
                title=payload.title,
                slug=payload.slug,
                excerpt=payload.excerpt,
                content=payload.content,
                cover_image=payload.cover_image,
                category_id=payload.category_id,
                tags=list(payload.tags or []),
                language_code=payload.language_code,
                # ---- VIP 内容属性：作者可自助设置（批次 16 放开）----
                is_vip_only=bool(payload.is_vip_only),
                required_vip_level=int(payload.required_vip_level or 0),
                # ---- 以下为强制性默认，前台无权设置 ----
                status=STATUS_DRAFT,
                post_type="article",
                hidden=False,
                is_featured=False,
                is_sticky=False,
                sort_order=0,
            ),
            user_id=user.id,
        )

    async def update_mine(
        self, db: AsyncSession, user, article_id: int, payload: MobileArticleUpdate
    ) -> dict:
        """更新自己的草稿/文章内容

        只传递白名单字段——`ArticleUpdate` 未收到的字段不会变化，
        因此即使有人伪造 `status` 也不会生效。
        """
        await self._mine_or_404(db, user, article_id)

        data = payload.model_dump(exclude_unset=True)
        allowed = {k: v for k, v in data.items() if v is not None}
        if not allowed:
            return await article_service.get_article(db, article_id, with_content=True)

        return await article_service.update_article(
            db, article_id, ArticleUpdate(**allowed)
        )

    async def delete_mine(self, db: AsyncSession, user, article_id: int) -> None:
        await self._mine_or_404(db, user, article_id)
        await article_service.delete_article(db, article_id)

    # ------------------------------------------------------------ 归属校验
    async def _mine_or_404(self, db: AsyncSession, user, article_id: int) -> Article:
        article = await article_crud.get(db, article_id)
        # 归属不符同样返回 404，避免泄露记录存在性
        if article is None or article.user != user.id:
            raise NotFoundError("文章不存在")
        return article

    # ------------------------------------------------------------ VIP 正文
    async def gated_content(
        self, db: AsyncSession, user, article_id: int, *, language_code: Optional[str] = None
    ) -> dict:
        """VIP 文章的正文（仅登录；等级达标或作者本人可读）

        公开详情对 VIP 文章**不下发正文**（见 ``article_service.apply_vip_gate``）：
        匿名 / SSR 首屏只会拿到摘要 + ``locked=True``，客户端拿到该标记后
        再带 token 调本端点取全文。
        """
        article = await self._public_or_404(db, article_id)
        required = 0
        if article.is_vip_only:
            required = max(int(article.required_vip_level or 0), 1)
            if article.user != user.id:
                from shared.services.core.membership import create_membership_service

                verdict = await create_membership_service(db).check_content_access(
                    user.id, article_id, required
                )
                if not verdict.get("has_access"):
                    raise ForbiddenError(f"需要 VIP 等级 {required} 才能阅读该文章")

        data = await article_service.get_article(db, article_id, language_code=language_code)
        return {
            "article_id": article_id,
            "is_vip_only": bool(article.is_vip_only),
            "required_vip_level": required,
            "content": data.get("content"),
        }

    # ------------------------------------------------------------ 点赞
    async def _public_or_404(self, db: AsyncSession, article_id: int) -> Article:
        """可公开交互的文章必须满足与公开详情相同的可见性规则"""
        article = await article_crud.get(db, article_id)
        if (
            article is None
            or article.status != STATUS_PUBLISHED
            or getattr(article, "hidden", False)
            or getattr(article, "deleted_at", None) is not None
        ):
            raise NotFoundError("文章不存在")
        return article

    async def toggle_like(self, db: AsyncSession, user, article_id: int) -> dict:
        """点赞 / 取消点赞（per-user 幂等切换）

        结构照抄 ``comment_service.toggle_like``：per-user 表去重 + 同步计数列；
        表换成 ``ArticleLike``（列名 ``user``/``article``），计数列是 ``Article.likes``
        （``mobile/user/stats`` 的 ``likes_received`` 依赖它）。
        """
        article = await self._public_or_404(db, article_id)

        existing = await db.scalar(
            select(ArticleLike).where(
                ArticleLike.article == article_id, ArticleLike.user == user.id
            )
        )
        if existing is not None:
            await db.delete(existing)
            article.likes = max(0, (article.likes or 0) - 1)
            liked = False
        else:
            db.add(ArticleLike(article=article_id, user=user.id, created_at=datetime.now()))
            article.likes = (article.likes or 0) + 1
            liked = True

        db.add(article)
        await db.commit()
        await db.refresh(article)
        return {"article_id": article_id, "liked": liked, "likes": article.likes or 0}

    async def like_status(self, db: AsyncSession, user, article_id: int) -> dict:
        """当前用户的点赞状态；匿名访客视为未点赞，仅返回计数"""
        article = await self._public_or_404(db, article_id)
        liked = False
        if user is not None:
            liked = (
                        await db.scalar(
                            select(func.count())
                            .select_from(ArticleLike)
                            .where(ArticleLike.article == article_id, ArticleLike.user == user.id)
                        )
                        or 0
                    ) > 0
        return {"article_id": article_id, "liked": liked, "likes": article.likes or 0}


mobile_article_service = MobileArticleService()
