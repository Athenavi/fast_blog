"""vip 模块业务逻辑：套餐 / 权益 / 订阅管理

`features` 列是 JSON 字符串（``String(255)``），schema 里以列表透出；
订阅状态约定：0=进行中 / 1=已过期 / 2=已取消。
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.marketing.vip.crud import (
    vip_feature_crud,
    vip_plan_crud,
    vip_subscription_crud,
)
from src.api.v3.modules.marketing.vip.schema import (
    PublicPlanOut,
    VipFeatureCreate,
    VipFeatureOut,
    VipFeatureUpdate,
    VipPlanCreate,
    VipPlanOut,
    VipPlanUpdate,
    VipSubscriptionCreate,
    VipSubscriptionOut,
)

logger = get_logger("vip")

#: 订阅状态
SUB_ACTIVE, SUB_EXPIRED, SUB_CANCELLED = 0, 1, 2


def _plan_out(row) -> dict:
    data = VipPlanOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    raw = getattr(row, "features", None)
    if isinstance(raw, str) and raw:
        try:
            data["features"] = json.loads(raw)
        except json.JSONDecodeError:
            data["features"] = [raw]
    return data


def _feature_out(row) -> dict:
    return VipFeatureOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _subscription_out(row) -> dict:
    return VipSubscriptionOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class VipService:
    """VIP 会员管理（marketing 域）"""

    # ------------------------------------------------------------ 套餐
    async def list_plans(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await vip_plan_crud.list(db, page=page, page_size=page_size, keyword=keyword)
        return [_plan_out(r) for r in rows], total

    async def create_plan(self, db: AsyncSession, payload: VipPlanCreate) -> dict:
        features = json.dumps(payload.features, ensure_ascii=False) if payload.features else None
        row = await vip_plan_crud.create(
            db,
            payload.model_dump(exclude={"features"}) | {"features": features,
                                                        "created_at": datetime.now(),
                                                        "updated_at": datetime.now()},
        )
        return _plan_out(row)

    async def update_plan(self, db: AsyncSession, plan_id: int, payload: VipPlanUpdate) -> dict:
        row = await vip_plan_crud.get(db, plan_id)
        if row is None:
            raise NotFoundError("套餐不存在")
        data = payload.model_dump(exclude_unset=True)
        if "features" in data:
            features = data.pop("features")
            data["features"] = json.dumps(features, ensure_ascii=False) if features else None
        updated = await vip_plan_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _plan_out(updated)

    async def delete_plan(self, db: AsyncSession, plan_id: int) -> None:
        if await vip_subscription_crud.exists(db, plan=plan_id):
            raise ConflictError("该套餐已有订阅记录，请先处理")
        row = await vip_plan_crud.get(db, plan_id)
        if row is None:
            raise NotFoundError("套餐不存在")
        await vip_plan_crud.remove(db, row)

    # ------------------------------------------------------------ 权益
    async def list_features(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await vip_feature_crud.list(db, page=page, page_size=page_size, keyword=keyword)
        return [_feature_out(r) for r in rows], total

    async def create_feature(self, db: AsyncSession, payload: VipFeatureCreate) -> dict:
        if await vip_feature_crud.exists(db, code=payload.code):
            raise ConflictError(f"权益代码已存在: {payload.code}")
        row = await vip_feature_crud.create(db, payload.model_dump() | {"created_at": datetime.now()})
        return _feature_out(row)

    async def update_feature(self, db: AsyncSession, feature_id: int, payload: VipFeatureUpdate) -> dict:
        row = await vip_feature_crud.get(db, feature_id)
        if row is None:
            raise NotFoundError("权益不存在")
        data = payload.model_dump(exclude_unset=True)
        if "code" in data and data["code"] != row.code:
            if await vip_feature_crud.exists(db, code=data["code"]):
                raise ConflictError(f"权益代码已存在: {data['code']}")
        updated = await vip_feature_crud.update(db, row, data)
        return _feature_out(updated)

    async def delete_feature(self, db: AsyncSession, feature_id: int) -> None:
        row = await vip_feature_crud.get(db, feature_id)
        if row is None:
            raise NotFoundError("权益不存在")
        await vip_feature_crud.remove(db, row)

    # ------------------------------------------------------------ 订阅
    async def list_subscriptions(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        status: Optional[int] = None,
    ) -> tuple[list[dict], int]:
        filters = {}
        if user_id is not None:
            filters["user"] = user_id
        if status is not None:
            filters["status"] = status
        rows, total = await vip_subscription_crud.list(
            db, page=page, page_size=page_size, filters=filters
        )
        return [_subscription_out(r) for r in rows], total

    async def create_subscription(self, db: AsyncSession, payload: VipSubscriptionCreate) -> dict:
        user = (await db.execute(select(User).where(User.id == payload.user_id))).scalar_one_or_none()
        if user is None:
            raise NotFoundError("用户不存在")
        plan = await vip_plan_crud.get(db, payload.plan_id)
        if plan is None:
            raise NotFoundError("套餐不存在")
        if not plan.is_active:
            raise BadRequestError("套餐已停用，无法开通")

        starts_at = payload.starts_at or datetime.now()
        expires_at = starts_at + timedelta(days=plan.duration_days or 0)
        row = await vip_subscription_crud.create(
            db,
            {
                "user": payload.user_id,
                "plan": payload.plan_id,
                "starts_at": starts_at,
                "expires_at": expires_at,
                "status": SUB_ACTIVE,
                "payment_amount": payload.payment_amount if payload.payment_amount is not None else plan.price,
                "transaction_id": payload.transaction_id,
                "created_at": datetime.now(),
            },
        )
        logger.info("VIP 订阅开通 user=%s plan=%s expires_at=%s", payload.user_id, plan.id, expires_at)
        return _subscription_out(row)

    async def cancel_subscription(self, db: AsyncSession, subscription_id: int) -> dict:
        row = await vip_subscription_crud.get(db, subscription_id)
        if row is None:
            raise NotFoundError("订阅不存在")
        if row.status == SUB_CANCELLED:
            raise BadRequestError("订阅已取消")
        updated = await vip_subscription_crud.update(db, row, {"status": SUB_CANCELLED})
        return _subscription_out(updated)

    # ------------------------------------------------------------ 前台公开读
    async def public_plans(self, db: AsyncSession) -> list[dict]:
        """前台 /vip 页公开读：上架套餐（level、price 升序），features 已合并等级匹配权益

        铁律：公开读不做数据范围过滤（不传 scope_user），只按 ``is_active`` 出上架内容。

        features 合并规则：套餐自身 ``features`` JSON 列表在前；其后追加
        ``VIPFeature.required_level <= 套餐 level`` 的激活权益展示名
        （required_level 升序、id 升序；取 name，缺省回退 code），
        与已有条目去重、保序。VIPFeature 无 plan_id 关联列，
        ``required_level <= level`` 是其唯一的套餐关联机制。
        """
        plan_rows, _ = await vip_plan_crud.list(
            db, page=1, page_size=0, filters={"is_active": True}, order_by="level", order="asc"
        )
        feature_rows, _ = await vip_feature_crud.list(
            db, page=1, page_size=0, filters={"is_active": True},
            order_by="required_level", order="asc",
        )
        benefits = [
            (f.required_level or 1, (f.name or "").strip() or (f.code or "").strip())
            for f in feature_rows
        ]
        benefits = [(req, text) for req, text in benefits if text]

        items: list[dict] = []
        for row in plan_rows:
            data = PublicPlanOut.model_validate(row, from_attributes=True).model_dump(mode="json")
            merged = list(data["features"] or [])
            level = data["level"] or 1
            for required_level, text in benefits:
                if required_level <= level and text not in merged:
                    merged.append(text)
            data["features"] = merged
            items.append(data)

        # DB 已按 level 升序；稳定排序补第二关键字 price 升序
        items.sort(key=lambda p: p["price"] if p["price"] is not None else 0)
        return items


vip_service = VipService()
