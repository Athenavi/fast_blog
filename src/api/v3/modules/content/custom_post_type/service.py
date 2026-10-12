"""custom_post_type 模块业务逻辑：自定义内容类型**与字段值**。

类型定义（`custom_post_types.fields`）与字段值（`custom_fields`，EAV）都在这里管理：
写入一律先过 `field_spec.validate_values` 按定义校验，非法输入直接 400（不静默丢弃）。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import CustomField
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.modules.content.custom_post_type.crud import custom_post_type_crud
from src.api.v3.modules.content.custom_post_type.field_spec import (
    parse_fields,
    validate_values,
)
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

    # ------------------------------------------------------------------ 字段值
    async def get_values(self, db: AsyncSession, type_id: int, content_id: int) -> dict:
        """读某内容实例的字段值；**按定义补齐**未填字段为 None，便于前端渲染表单。"""
        row = await custom_post_type_crud.get(db, type_id)
        if row is None:
            raise NotFoundError("内容类型不存在")

        definitions = parse_fields(getattr(row, "fields", None))
        stored = (
            await db.execute(
                select(CustomField).where(
                    CustomField.post_type_id == type_id,
                    CustomField.content_id == content_id,
                )
            )
        ).scalars().all()
        current = {str(item.field_name): item.field_value for item in stored}
        return {
            "type_id": type_id,
            "content_id": content_id,
            "values": {
                str(spec.get("key")): current.get(str(spec.get("key")))
                for spec in definitions
                if spec.get("key")
            },
        }

    async def set_values(
        self,
        db: AsyncSession,
        type_id: int,
        content_id: int,
        values: Dict[str, Any],
        *,
        user_id: Optional[int] = None,
    ) -> dict:
        """写字段值：按类型定义校验/规范化后 upsert。

        校验由 ``field_spec.validate_values`` 完成 —— 必填缺失、类型不符、选项外取值、
        **未定义的字段名**都会 400（拼错字段名会静默丢数据，这里宁可报错）。
        """
        row = await custom_post_type_crud.get(db, type_id)
        if row is None:
            raise NotFoundError("内容类型不存在")

        definitions = parse_fields(getattr(row, "fields", None))
        if not definitions:
            raise BadRequestError("该内容类型尚未定义字段，无法写入字段值")

        normalized = validate_values(definitions, values)

        existing_rows = (
            await db.execute(
                select(CustomField).where(
                    CustomField.post_type_id == type_id,
                    CustomField.content_id == content_id,
                )
            )
        ).scalars().all()
        by_name = {str(item.field_name): item for item in existing_rows}

        for key, value in normalized.items():
            item = by_name.get(key)
            if item is None:
                db.add(
                    CustomField(
                        user=user_id,
                        post_type_id=type_id,
                        content_id=content_id,
                        field_name=key,
                        field_value=value,
                    )
                )
            else:
                item.field_value = value
        await db.commit()
        return {"type_id": type_id, "content_id": content_id, "updated": sorted(normalized)}


custom_post_type_service = CustomPostTypeService()
