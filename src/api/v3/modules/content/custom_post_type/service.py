"""custom_post_type 模块业务逻辑：自定义内容类型

`custom_fields`（字段值）挂在具体内容上，属内容编辑侧，本模块只管理类型定义。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.content.custom_post_type.crud import custom_post_type_crud
from src.api.v3.modules.content.custom_post_type.schema import (
    CustomPostTypeCreate,
    CustomPostTypeOut,
    CustomPostTypeUpdate,
)


def _to_out(row) -> dict:
    return CustomPostTypeOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class CustomPostTypeService:
    """自定义内容类型（content 域）"""

    async def list_types(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await custom_post_type_crud.list(
            db, page=page, page_size=page_size, keyword=keyword
        )
        return [_to_out(r) for r in rows], total

    async def create_type(self, db: AsyncSession, payload: CustomPostTypeCreate) -> dict:
        if await custom_post_type_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"类型标识已存在: {payload.slug}")
        row = await custom_post_type_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_out(row)

    async def update_type(self, db: AsyncSession, type_id: int, payload: CustomPostTypeUpdate) -> dict:
        row = await custom_post_type_crud.get(db, type_id)
        if row is None:
            raise NotFoundError("内容类型不存在")
        updated = await custom_post_type_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _to_out(updated)

    async def delete_type(self, db: AsyncSession, type_id: int) -> None:
        row = await custom_post_type_crud.get(db, type_id)
        if row is None:
            raise NotFoundError("内容类型不存在")
        await custom_post_type_crud.remove(db, row)


custom_post_type_service = CustomPostTypeService()
