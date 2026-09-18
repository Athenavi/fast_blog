"""mobile/article 的用户投稿逻辑

复用 ``modules/content/article`` 的 ``article_service``，在其之上加三层约束：

1. **归属**：列表只查自己的，详情/更新/删除先校验 ``article.user == current.id``，
   不符返回 404（不泄露存在性）。
2. **只能存草稿**：创建时强制 ``status = STATUS_DRAFT``；更新时**忽略**任何改状态的企图。
   发布走后台 ``/content/article/{id}/publish``，即"投稿 → 审核 → 发布"的分离。
3. **管理字段归零**：`is_featured` / `is_sticky` / `hidden` / `is_vip_only` /
   `required_vip_level` / `sort_order` 一律由服务端设定，前台无法自助设置。
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.content.article.crud import article_crud
from src.api.v3.modules.content.article.schema import ArticleCreate, ArticleUpdate
from src.api.v3.modules.content.article.service import STATUS_DRAFT, article_service
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
                # ---- 以下为强制性默认，前台无权设置 ----
                status=STATUS_DRAFT,
                post_type="article",
                hidden=False,
                is_featured=False,
                is_sticky=False,
                is_vip_only=False,
                required_vip_level=0,
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


mobile_article_service = MobileArticleService()
