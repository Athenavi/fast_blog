"""ad 模块路由（T5-11 批次 1：自 astro `admin/ads` 能力域新建）

::

    GET    /api/v3/marketing/ad/placement            广告位列表
    POST   /api/v3/marketing/ad/placement            新建广告位
    PUT    /api/v3/marketing/ad/placement/{id}       更新广告位
    DELETE /api/v3/marketing/ad/placement/{id}       删除广告位（须无广告）
    GET    /api/v3/marketing/ad                      广告列表
    POST   /api/v3/marketing/ad                      新建广告
    PUT    /api/v3/marketing/ad/{ad_id}              更新广告
    DELETE /api/v3/marketing/ad/{ad_id}              删除广告
    GET    /api/v3/marketing/ad/stats                投放统计（点击/曝光/预算）

权限码：``module_marketing:ad:view/create/edit/delete``。
点击/曝光明细（ad_clicks / ad_impressions）的公开上报端点属前台侧，随批次后续补充。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.marketing.ad.schema import (
    AdCreate,
    AdPlacementCreate,
    AdPlacementUpdate,
    AdUpdate,
)
from src.api.v3.modules.marketing.ad.service import ad_service

router = APIRouter(prefix="/ad", tags=["marketing-ad"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 广告位（静态路径前置）
@router.get("/placement", response_model=ResponseModel, summary="广告位列表")
async def list_placements(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await ad_service.list_placements(db, page=page, page_size=page_size, keyword=keyword)
    return resp.success_page(items, total, page, page_size)


@router.post("/placement", response_model=ResponseModel, summary="新建广告位")
async def create_placement(
    db: DBSession,
    payload: AdPlacementCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_CREATE),
) -> dict:
    return resp.success(await ad_service.create_placement(db, payload), msg="已创建")


@router.put("/placement/{placement_id}", response_model=ResponseModel, summary="更新广告位")
async def update_placement(
    placement_id: int,
    payload: AdPlacementUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_EDIT),
) -> dict:
    return resp.success(await ad_service.update_placement(db, placement_id, payload), msg="已保存")


@router.delete("/placement/{placement_id}", response_model=ResponseModel, summary="删除广告位")
async def delete_placement(
    placement_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_DELETE),
) -> dict:
    await ad_service.delete_placement(db, placement_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 统计（静态路径前置）
@router.get("/stats", response_model=ResponseModel, summary="投放统计")
async def ad_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_VIEW),
) -> dict:
    return resp.success(await ad_service.stats(db))


# ---------------------------------------------------------------- 广告
@router.get("", response_model=ResponseModel, summary="广告列表")
async def list_ads(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    placement_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await ad_service.list_ads(
        db, page=page, page_size=page_size, keyword=keyword,
        placement_id=placement_id, is_active=is_active,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建广告")
async def create_ad(
    db: DBSession,
    payload: AdCreate,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_CREATE),
) -> dict:
    return resp.success(await ad_service.create_ad(db, payload), msg="已创建")


@router.put("/{ad_id}", response_model=ResponseModel, summary="更新广告")
async def update_ad(
    ad_id: int,
    payload: AdUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_EDIT),
) -> dict:
    return resp.success(await ad_service.update_ad(db, ad_id, payload), msg="已保存")


@router.delete("/{ad_id}", response_model=ResponseModel, summary="删除广告")
async def delete_ad(
    ad_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AD_DELETE),
) -> dict:
    await ad_service.delete_ad(db, ad_id)
    return resp.success(None, msg="已删除")
