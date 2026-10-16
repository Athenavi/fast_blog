"""block_pattern 模块业务逻辑：区块模板库"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.extension.block_pattern.crud import block_pattern_crud
from src.api.v3.modules.extension.block_pattern.schema import (
    BlockPatternCreate,
    BlockPatternOut,
    BlockPatternUpdate,
)


def _to_out(row) -> dict:
    return BlockPatternOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class BlockPatternService:
    """区块模板（extension 域；创建者可管理自己的，管理端按权限码管理公开库）"""

    async def list_patterns(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: Optional[str] = None, category: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        filters = {"category": category} if category else {}
        rows, total = await block_pattern_crud.list(
            db, page=page, page_size=page_size, keyword=keyword, filters=filters
        )
        return [_to_out(r) for r in rows], total

    async def create_pattern(self, db: AsyncSession, payload: BlockPatternCreate, *, user_id: int) -> dict:
        row = await block_pattern_crud.create(
            db,
            payload.model_dump()
            | {"user_id": user_id, "created_at": datetime.now(), "updated_at": datetime.now()},
        )
        return _to_out(row)

    async def update_pattern(self, db: AsyncSession, pattern_id: int, payload: BlockPatternUpdate) -> dict:
        row = await block_pattern_crud.get(db, pattern_id)
        if row is None:
            raise NotFoundError("区块模板不存在")
        updated = await block_pattern_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _to_out(updated)

    async def delete_pattern(self, db: AsyncSession, pattern_id: int) -> None:
        row = await block_pattern_crud.get(db, pattern_id)
        if row is None:
            raise NotFoundError("区块模板不存在")
        await block_pattern_crud.remove(db, row)


block_pattern_service = BlockPatternService()
