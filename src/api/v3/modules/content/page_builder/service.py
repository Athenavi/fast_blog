"""page_builder 模块业务逻辑：可视化页面搭建管理

- ``blocks_data``：入参块数组，落库 ``json.dumps``，出参由 ``PageBuilderOut`` 解析回数组
- ``slug`` 唯一（DB unique 索引），冲突抛 ``ConflictError``（409）；创建后锁定
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.content.page_builder.crud import page_builder_crud
from src.api.v3.modules.content.page_builder.schema import (
    PageBuilderCreate,
    PageBuilderOut,
    PageBuilderUpdate,
)


def _to_out(row) -> dict:
    return PageBuilderOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _dump_blocks(blocks) -> str:
    return json.dumps(blocks or [], ensure_ascii=False)


class PageBuilderService:
    """页面搭建管理（content 域）"""

    async def list_pages(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_published: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await page_builder_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"is_published": is_published},
        )
        return [_to_out(r) for r in rows], total

    async def get_page(self, db: AsyncSession, page_id: int) -> dict:
        row = await page_builder_crud.get(db, page_id)
        if row is None:
            raise NotFoundError("搭建页面不存在")
        return _to_out(row)

    async def create_page(self, db: AsyncSession, payload: PageBuilderCreate) -> dict:
        if await page_builder_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"页面标识已存在: {payload.slug}")
        row = await page_builder_crud.create(
            db,
            payload.model_dump(exclude={"blocks_data"})
            | {
                "blocks_data": _dump_blocks(payload.blocks_data),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _to_out(row)

    async def update_page(self, db: AsyncSession, page_id: int, payload: PageBuilderUpdate) -> dict:
        row = await page_builder_crud.get(db, page_id)
        if row is None:
            raise NotFoundError("搭建页面不存在")
        data = payload.model_dump(exclude_unset=True)
        if "blocks_data" in payload.model_fields_set:
            data["blocks_data"] = _dump_blocks(payload.blocks_data)
        updated = await page_builder_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _to_out(updated)

    async def delete_page(self, db: AsyncSession, page_id: int) -> None:
        row = await page_builder_crud.get(db, page_id)
        if row is None:
            raise NotFoundError("搭建页面不存在")
        await page_builder_crud.remove(db, row)

    async def set_published(self, db: AsyncSession, page_id: int, is_published: bool) -> dict:
        row = await page_builder_crud.get(db, page_id)
        if row is None:
            raise NotFoundError("搭建页面不存在")
        updated = await page_builder_crud.update(
            db, row, {"is_published": is_published, "updated_at": datetime.now()}
        )
        return _to_out(updated)


page_builder_service = PageBuilderService()
