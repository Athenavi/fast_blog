"""ad 模块业务逻辑：广告位与广告的管理（投放点击/曝光记录由前台端点后续补充）"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.ad import Ad, AdPlacement
from src.api.v3.core.base_schema import SchemaBase
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.marketing.ad.crud import ad_crud, ad_placement_crud
from src.api.v3.modules.marketing.ad.schema import (
    AdCreate,
    AdOut,
    AdPlacementCreate,
    AdPlacementOut,
    AdPlacementUpdate,
    AdStatsOut,
    AdUpdate,
)

logger = get_logger("ad")


def _to_dict(row, out_cls: type[SchemaBase]) -> dict:
    """ORM 行 → 响应字典（Numeric 转 float）"""
    data = out_cls.model_validate(row, from_attributes=True).model_dump(mode="json")
    return data


class AdService:
    """广告管理（marketing 域）"""

    # ------------------------------------------------------------ 广告位
    async def list_placements(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await ad_placement_crud.list(db, page=page, page_size=page_size, keyword=keyword)
        return [_to_dict(r, AdPlacementOut) for r in rows], total

    async def create_placement(self, db: AsyncSession, payload: AdPlacementCreate) -> dict:
        if await ad_placement_crud.exists(db, code=payload.code):
            raise ConflictError(f"广告位代码已存在: {payload.code}")
        row = await ad_placement_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_dict(row, AdPlacementOut)

    async def update_placement(self, db: AsyncSession, placement_id: int, payload: AdPlacementUpdate) -> dict:
        row = await ad_placement_crud.get(db, placement_id)
        if row is None:
            raise NotFoundError("广告位不存在")
        data = payload.model_dump(exclude_unset=True)
        if "code" in data and data["code"] != row.code:
            if await ad_placement_crud.exists(db, code=data["code"]):
                raise ConflictError(f"广告位代码已存在: {data['code']}")
        updated = await ad_placement_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _to_dict(updated, AdPlacementOut)

    async def delete_placement(self, db: AsyncSession, placement_id: int) -> None:
        if await ad_crud.exists(db, placement_id=placement_id):
            raise ConflictError("该广告位下仍有广告，请先处理")
        row = await ad_placement_crud.get(db, placement_id)
        if row is None:
            raise NotFoundError("广告位不存在")
        await ad_placement_crud.remove(db, row)

    # ------------------------------------------------------------ 广告
    async def list_ads(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        placement_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        filters = {}
        if placement_id is not None:
            filters["placement_id"] = placement_id
        if is_active is not None:
            filters["is_active"] = is_active
        rows, total = await ad_crud.list(db, page=page, page_size=page_size, keyword=keyword, filters=filters)
        return [_to_dict(r, AdOut) for r in rows], total

    async def create_ad(self, db: AsyncSession, payload: AdCreate) -> dict:
        if payload.placement_id is not None:
            await self._placement_or_404(db, payload.placement_id)
        if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
            raise BadRequestError("开始时间不能晚于结束时间")
        row = await ad_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_dict(row, AdOut)

    async def update_ad(self, db: AsyncSession, ad_id: int, payload: AdUpdate) -> dict:
        row = await ad_crud.get(db, ad_id)
        if row is None:
            raise NotFoundError("广告不存在")
        data = payload.model_dump(exclude_unset=True)
        start = data.get("start_date", row.start_date)
        end = data.get("end_date", row.end_date)
        if start and end and start > end:
            raise BadRequestError("开始时间不能晚于结束时间")
        updated = await ad_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _to_dict(updated, AdOut)

    async def delete_ad(self, db: AsyncSession, ad_id: int) -> None:
        row = await ad_crud.get(db, ad_id)
        if row is None:
            raise NotFoundError("广告不存在")
        await ad_crud.remove(db, row)

    async def stats(self, db: AsyncSession) -> dict:
        total_ads = (await db.execute(select(func.count()).select_from(Ad))).scalar() or 0
        active_ads = (await db.execute(
            select(func.count()).select_from(Ad).where(Ad.is_active.is_(True))
        )).scalar() or 0
        total_clicks = (await db.execute(select(func.coalesce(func.sum(Ad.click_count), 0)))).scalar() or 0
        total_impressions = (await db.execute(
            select(func.coalesce(func.sum(Ad.impression_count), 0))
        )).scalar() or 0
        total_budget = float((await db.execute(
            select(func.coalesce(func.sum(Ad.budget), 0))
        )).scalar() or 0)
        stats = AdStatsOut(
            total_ads=int(total_ads),
            active_ads=int(active_ads),
            total_clicks=int(total_clicks),
            total_impressions=int(total_impressions),
            total_budget=total_budget,
        )
        return stats.model_dump()

    # ------------------------------------------------------------ 归属校验
    async def _placement_or_404(self, db: AsyncSession, placement_id: int) -> AdPlacement:
        row = await ad_placement_crud.get(db, placement_id)
        if row is None:
            raise NotFoundError("广告位不存在")
        return row


ad_service = AdService()
