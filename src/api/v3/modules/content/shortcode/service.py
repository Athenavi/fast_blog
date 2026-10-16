"""shortcode 模块业务逻辑：短代码库（[code] -> 预定义内容片段）

code 唯一；创建后锁定（更新 schema 不含 code，语义对齐 custom_post_type 的 slug）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.content.shortcode.crud import shortcode_crud
from src.api.v3.modules.content.shortcode.schema import (
    ShortcodeCreate,
    ShortcodeOut,
    ShortcodeUpdate,
)


def _to_out(row) -> dict:
    return ShortcodeOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class ShortcodeService:
    """短代码库（content 域）"""

    async def list_shortcodes(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await shortcode_crud.list(
            db, page=page, page_size=page_size, keyword=keyword,
            filters={"is_active": is_active},
        )
        return [_to_out(r) for r in rows], total

    async def create_shortcode(self, db: AsyncSession, payload: ShortcodeCreate) -> dict:
        if await shortcode_crud.exists(db, code=payload.code):
            raise ConflictError(f"短代码标识已存在: {payload.code}")
        row = await shortcode_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_out(row)

    async def update_shortcode(
        self, db: AsyncSession, shortcode_id: int, payload: ShortcodeUpdate
    ) -> dict:
        row = await shortcode_crud.get(db, shortcode_id)
        if row is None:
            raise NotFoundError("短代码不存在")
        updated = await shortcode_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _to_out(updated)

    async def delete_shortcode(self, db: AsyncSession, shortcode_id: int) -> None:
        row = await shortcode_crud.get(db, shortcode_id)
        if row is None:
            raise NotFoundError("短代码不存在")
        await shortcode_crud.remove(db, row)


shortcode_service = ShortcodeService()
