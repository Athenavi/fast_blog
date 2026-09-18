"""page 模块业务逻辑

页面正文内联在 ``pages.content``，无需额外表；发布态用 ``status`` + ``published_at``。
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.page.pages import Pages
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.content.page.crud import page_crud
from src.api.v3.modules.content.page.schema import (
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    PageCreate,
    PageUpdate,
)

logger = get_logger("page")


def _out(page: Pages, *, with_content: bool = False) -> dict:
    data = {
        "id": page.id,
        "title": page.title,
        "slug": page.slug,
        "excerpt": page.excerpt,
        "template": page.template,
        "status": page.status,
        "author_id": page.author_id,
        "parent_id": page.parent_id,
        "order_index": page.order_index or 0,
        "meta_title": page.meta_title,
        "meta_description": page.meta_description,
        "meta_keywords": page.meta_keywords,
        "published_at": page.published_at,
        "created_at": page.created_at,
        "updated_at": page.updated_at,
    }
    if with_content:
        data["content"] = page.content
    return data


class PageService:
    """CMS 页面管理"""

    @staticmethod
    def _validate_status(status: Optional[int]) -> None:
        if status is not None and status not in (STATUS_DRAFT, STATUS_PUBLISHED):
            raise BadRequestError("status 只能是 0（草稿）或 1（已发布）")

    async def list_pages(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        parent_id: Optional[int] = None,
        order_by: Optional[str] = None,
        order: str = "asc",
    ) -> Tuple[List[dict], int]:
        items, total = await page_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"status": status, "parent_id": parent_id},
            order_by=order_by or "order_index",
            order=order,
        )
        return [_out(page) for page in items], total

    async def get_page(self, db: AsyncSession, page_id: int) -> dict:
        page = await page_crud.get(db, page_id)
        if page is None:
            raise NotFoundError("页面不存在")
        return _out(page, with_content=True)

    async def create_page(
        self, db: AsyncSession, payload: PageCreate, *, author_id: Optional[int] = None
    ) -> dict:
        self._validate_status(payload.status)
        if payload.slug and await page_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"页面 slug {payload.slug} 已存在")

        now = datetime.now()
        data = payload.model_dump()
        data.update(
            {
                "author_id": author_id,
                "created_at": now,
                "updated_at": now,
                "published_at": now if payload.status == STATUS_PUBLISHED else None,
            }
        )
        page = await page_crud.create(db, data)
        return _out(page, with_content=True)

    async def update_page(self, db: AsyncSession, page_id: int, payload: PageUpdate) -> dict:
        page = await page_crud.get(db, page_id)
        if page is None:
            raise NotFoundError("页面不存在")

        fields_set = payload.model_fields_set
        self._validate_status(payload.status if "status" in fields_set else None)

        data = payload.model_dump(exclude_unset=True)
        if "slug" in fields_set and payload.slug:
            existing = await page_crud.get_by(db, slug=payload.slug)
            if existing is not None and existing.id != page_id:
                raise ConflictError(f"页面 slug {payload.slug} 已存在")
        if data.get("status") == STATUS_PUBLISHED and page.published_at is None:
            data["published_at"] = datetime.now()
        data["updated_at"] = datetime.now()

        page = await page_crud.update(db, page, data)
        return _out(page, with_content=True)

    async def delete_page(self, db: AsyncSession, page_id: int) -> None:
        page = await page_crud.get(db, page_id)
        if page is None:
            raise NotFoundError("页面不存在")
        await page_crud.remove(db, page)

    async def batch_delete(self, db: AsyncSession, ids: List[int]) -> int:
        count = 0
        for page_id in ids:
            try:
                await self.delete_page(db, page_id)
                count += 1
            except NotFoundError:
                continue
        return count

    async def set_published(self, db: AsyncSession, page_id: int, publish: bool) -> dict:
        page = await page_crud.get(db, page_id)
        if page is None:
            raise NotFoundError("页面不存在")

        if publish:
            data = {
                "status": STATUS_PUBLISHED,
                "published_at": page.published_at or datetime.now(),
                "updated_at": datetime.now(),
            }
        else:
            data = {"status": STATUS_DRAFT, "updated_at": datetime.now()}

        page = await page_crud.update(db, page, data)
        return _out(page)

    # ------------------------------------------------------------------ 公开读
    async def public_list(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 50
    ) -> Tuple[List[dict], int]:
        items, total = await page_crud.list(
            db,
            page=page,
            page_size=page_size,
            filters={"status": STATUS_PUBLISHED},
            order_by="order_index",
            order="asc",
        )
        return [_out(item) for item in items], total

    async def public_detail_by_slug(self, db: AsyncSession, slug: str) -> dict:
        page = await page_crud.get_by(db, slug=slug)
        if page is None or page.status != STATUS_PUBLISHED:
            raise NotFoundError("页面不存在或未发布")
        return _out(page, with_content=True)

    async def public_detail(self, db: AsyncSession, page_id: int) -> dict:
        page = await page_crud.get(db, page_id)
        if page is None or page.status != STATUS_PUBLISHED:
            raise NotFoundError("页面不存在或未发布")
        return _out(page, with_content=True)


page_service = PageService()
