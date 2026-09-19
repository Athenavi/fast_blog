"""vip 模块路由（T5-11 批次 1：自 astro `admin/vip` 能力域新建）

::

    GET    /api/v3/marketing/vip/plan                 套餐列表
    POST   /api/v3/marketing/vip/plan                 新建套餐
    PUT    /api/v3/marketing/vip/plan/{plan_id}       更新套餐
    DELETE /api/v3/marketing/vip/plan/{plan_id}       删除套餐（须无订阅）
    GET    /api/v3/marketing/vip/feature              权益列表
    POST   /api/v3/marketing/vip/feature              新建权益
    PUT    /api/v3/marketing/vip/feature/{feature_id} 更新权益
    DELETE /api/v3/marketing/vip/feature/{feature_id} 删除权益
    GET    /api/v3/marketing/vip/subscription         订阅列表
    POST   /api/v3/marketing/vip/subscription         手动开通订阅
    POST   /api/v3/marketing/vip/subscription/{id}/cancel  取消订阅

权限码：``module_marketing:vip:view/create/edit/delete``。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.marketing.vip.schema import (
    VipFeatureCreate,
    VipFeatureUpdate,
    VipPlanCreate,
    VipPlanUpdate,
    VipSubscriptionCreate,
)
from src.api.v3.modules.marketing.vip.service import vip_service

router = APIRouter(prefix="/vip", tags=["marketing-vip"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 套餐（静态路径前置）
@router.get("/plan", response_model=ResponseModel, summary="套餐列表")
async def list_plans(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await vip_service.list_plans(db, page=page, page_size=page_size, keyword=keyword)
    return resp.success_page(items, total, page, page_size)


@router.post("/plan", response_model=ResponseModel, summary="新建套餐")
async def create_plan(
    db: DBSession,
    payload: VipPlanCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_CREATE),
) -> dict:
    return resp.success(await vip_service.create_plan(db, payload), msg="已创建")


@router.put("/plan/{plan_id}", response_model=ResponseModel, summary="更新套餐")
async def update_plan(
    plan_id: int,
    payload: VipPlanUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_EDIT),
) -> dict:
    return resp.success(await vip_service.update_plan(db, plan_id, payload), msg="已保存")


@router.delete("/plan/{plan_id}", response_model=ResponseModel, summary="删除套餐")
async def delete_plan(
    plan_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_DELETE),
) -> dict:
    await vip_service.delete_plan(db, plan_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 权益（静态路径前置）
@router.get("/feature", response_model=ResponseModel, summary="权益列表")
async def list_features(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await vip_service.list_features(db, page=page, page_size=page_size, keyword=keyword)
    return resp.success_page(items, total, page, page_size)


@router.post("/feature", response_model=ResponseModel, summary="新建权益")
async def create_feature(
    db: DBSession,
    payload: VipFeatureCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_CREATE),
) -> dict:
    return resp.success(await vip_service.create_feature(db, payload), msg="已创建")


@router.put("/feature/{feature_id}", response_model=ResponseModel, summary="更新权益")
async def update_feature(
    feature_id: int,
    payload: VipFeatureUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_EDIT),
) -> dict:
    return resp.success(await vip_service.update_feature(db, feature_id, payload), msg="已保存")


@router.delete("/feature/{feature_id}", response_model=ResponseModel, summary="删除权益")
async def delete_feature(
    feature_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_DELETE),
) -> dict:
    await vip_service.delete_feature(db, feature_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 订阅（静态路径前置）
@router.get("/subscription", response_model=ResponseModel, summary="订阅列表")
async def list_subscriptions(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None),
    status: Optional[int] = Query(default=None, description="0 进行中 / 1 已过期 / 2 已取消"),
) -> dict:
    items, total = await vip_service.list_subscriptions(
        db, page=page, page_size=page_size, user_id=user_id, status=status
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/subscription", response_model=ResponseModel, summary="手动开通订阅")
async def create_subscription(
    db: DBSession,
    payload: VipSubscriptionCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_CREATE),
) -> dict:
    return resp.success(await vip_service.create_subscription(db, payload), msg="已开通")


@router.post("/subscription/{subscription_id}/cancel", response_model=ResponseModel, summary="取消订阅")
async def cancel_subscription(
    subscription_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.VIP_EDIT),
) -> dict:
    return resp.success(await vip_service.cancel_subscription(db, subscription_id), msg="已取消")
