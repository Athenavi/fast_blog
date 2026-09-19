"""site 模块业务逻辑：多站点管理

- slug 是站点稳定标识，创建后锁定（与 custom_post_type 的 slug 语义一致）；
- 唯一键冲突（slug / domain）返回 409；
- ``is_default`` 全站唯一：设为默认时自动取消其它站点的默认标记。
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.system.site.crud import site_crud
from src.api.v3.modules.system.site.schema import (
    SiteCreate,
    SiteOut,
    SiteUpdate,
)


def _dump_json(value):  # noqa: ANN001, ANN202 - JSON 列写入前序列化
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _to_out(row) -> dict:
    return SiteOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class SiteService:
    """多站点管理（system 域）"""

    async def list_sites(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20,
        keyword: Optional[str] = None, is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await site_crud.list(
            db, page=page, page_size=page_size, keyword=keyword, filters={"is_active": is_active}
        )
        return [_to_out(r) for r in rows], total

    async def create_site(self, db: AsyncSession, payload: SiteCreate) -> dict:
        if await site_crud.exists(db, slug=payload.slug):
            raise ConflictError(f"站点标识已存在: {payload.slug}")
        if await site_crud.exists(db, domain=payload.domain):
            raise ConflictError(f"站点域名已存在: {payload.domain}")
        data = payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        data["additional_domains"] = _dump_json(data.get("additional_domains"))
        data["settings"] = _dump_json(data.get("settings"))
        row = await site_crud.create(db, data)
        if payload.is_default:
            await self._unset_other_defaults(db, row.id)
            await db.commit()
        return _to_out(row)

    async def update_site(self, db: AsyncSession, site_id: int, payload: SiteUpdate) -> dict:
        row = await site_crud.get(db, site_id)
        if row is None:
            raise NotFoundError("站点不存在")
        data = payload.model_dump(exclude_unset=True)
        if "domain" in data and data["domain"] and data["domain"] != row.domain:
            if await site_crud.exists(db, domain=data["domain"]):
                raise ConflictError(f"站点域名已存在: {data['domain']}")
        if "additional_domains" in data:
            data["additional_domains"] = _dump_json(data["additional_domains"])
        if "settings" in data:
            data["settings"] = _dump_json(data["settings"])
        data |= {"updated_at": datetime.now()}
        updated = await site_crud.update(db, row, data)
        if data.get("is_default"):
            await self._unset_other_defaults(db, site_id)
            await db.commit()
            await db.refresh(updated)
        return _to_out(updated)

    async def delete_site(self, db: AsyncSession, site_id: int) -> None:
        row = await site_crud.get(db, site_id)
        if row is None:
            raise NotFoundError("站点不存在")
        if row.is_default:
            raise ConflictError("默认站点不可删除，请先把默认标记移到其它站点")
        await site_crud.remove(db, row)

    @staticmethod
    async def _unset_other_defaults(db: AsyncSession, keep_site_id: int) -> None:
        """单一默认站点：把其它站点的 is_default 清掉"""
        rows, _total = await site_crud.list(
            db, page=1, page_size=0, filters={"is_default": True}
        )
        for other in rows:
            if other.id != keep_site_id:
                other.is_default = False
                other.updated_at = datetime.now()
                db.add(other)


site_service = SiteService()
