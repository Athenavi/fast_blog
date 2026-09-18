"""page 模块路由

RESTful 主路径 + 兼容别名::

    GET    /api/v3/content/page/public/list        公开页面列表（无鉴权）
    GET    /api/v3/content/page/public/slug/{slug} 公开页面详情（无鉴权）
    GET    /api/v3/content/page                    页面列表
    POST   /api/v3/content/page                    新建页面
    POST   /api/v3/content/page/batch/delete       批量删除
    GET    /api/v3/content/page/{page_id}          页面详情
    PUT    /api/v3/content/page/{page_id}          更新页面
    DELETE /api/v3/content/page/{page_id}          删除页面
    POST   /api/v3/content/page/{page_id}/publish  发布 / 撤回

权限码：``page:view`` / ``page:create`` / ``page:edit`` / ``page:delete`` / ``page:publish``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.page.schema import (
    PageBatchDeleteRequest,
    PageCreate,
    PagePublishRequest,
    PageUpdate,
)
from src.api.v3.modules.content.page.service import page_service

router = APIRouter(prefix="/page", tags=["content-page"], route_class=OperationLogRoute)


# ─────────────────────────── 公开读（无鉴权）───────────────────────────
@router.get("/public/list", response_model=ResponseModel, summary="公开页面列表")
async def public_pages(
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    items, total = await page_service.public_list(db, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.get("/public/slug/{slug}", response_model=ResponseModel, summary="按 slug 取公开页面")
async def public_page_by_slug(slug: str, db: DBSession) -> dict:
    return resp.success(await page_service.public_detail_by_slug(db, slug))


# ─────────────────────────── 管理端：列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="页面列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 页面列表",
)
async def list_pages(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_VIEW),
    status: Optional[int] = Query(default=None),
    parent_id: Optional[int] = Query(default=None),
) -> dict:
    items, total = await page_service.list_pages(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        status=status,
        parent_id=parent_id,
        order_by=page.order_by,
        order=page.order or "asc",
        scope_user=_current,
    )
    return resp.success_page(items, total, page.page, page.page_size)


# ─────────────────────────── 管理端：新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建页面")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建页面",
)
async def create_page(
    payload: PageCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAGE_CREATE),
) -> dict:
    return resp.success(await page_service.create_page(db, payload, author_id=current.id), msg="创建成功")


# ─────────────────────────── 批量删除（静态路径优先）───────────────────────────
@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除页面")
async def batch_delete_pages(
    payload: PageBatchDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_DELETE),
) -> dict:
    affected = await page_service.batch_delete(db, payload.ids)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 个页面")


# ─────────────────────────── 详情 / 更新 / 删除 / 发布 ───────────────────────────
@router.get("/{page_id}", response_model=ResponseModel, summary="页面详情")
@router.get(
    "/detail/{page_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 页面详情",
)
async def get_page(
    page_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_VIEW),
) -> dict:
    return resp.success(await page_service.get_page(db, page_id, scope_user=_current))


@router.put("/{page_id}", response_model=ResponseModel, summary="更新页面")
@router.put(
    "/update/{page_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新页面",
)
async def update_page(
    page_id: int,
    payload: PageUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_EDIT),
) -> dict:
    return resp.success(await page_service.update_page(db, page_id, payload), msg="更新成功")


@router.delete("/{page_id}", response_model=ResponseModel, summary="删除页面")
async def delete_page(
    page_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_DELETE),
) -> dict:
    await page_service.delete_page(db, page_id)
    return resp.success(None, msg="已删除")


@router.post("/{page_id}/publish", response_model=ResponseModel, summary="发布 / 撤回页面")
async def publish_page(
    page_id: int,
    payload: PagePublishRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_PUBLISH),
) -> dict:
    data = await page_service.set_published(db, page_id, payload.publish)
    return resp.success(data, msg="已发布" if payload.publish else "已转草稿")
