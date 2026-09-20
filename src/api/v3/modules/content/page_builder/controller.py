"""page_builder 模块路由（T5-11 批次 6：页面搭建管理）

::

    GET    /api/v3/content/page-builder                     搭建页面列表（分页 + keyword + is_published 过滤）
    POST   /api/v3/content/page-builder                     新建搭建页面
    GET    /api/v3/content/page-builder/{page_id}           搭建页面详情（含块数据）
    PUT    /api/v3/content/page-builder/{page_id}           更新搭建页面（slug 创建后锁定，不可改）
    DELETE /api/v3/content/page-builder/{page_id}           删除搭建页面
    POST   /api/v3/content/page-builder/{page_id}/publish   发布 / 撤回（body ``{is_published: bool}``）

权限码：``module_content:page_builder:view/create/edit/delete``。
``blocks_data`` 入参为块对象数组，落库 json.dumps，出参解析回数组。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.page_builder.schema import (
    PageBuilderCreate,
    PageBuilderPublishRequest,
    PageBuilderUpdate,
)
from src.api.v3.modules.content.page_builder.service import page_builder_service

router = APIRouter(
    prefix="/page-builder", tags=["content-page-builder"], route_class=OperationLogRoute
)


@router.get("", response_model=ResponseModel, summary="搭建页面列表")
async def list_pages(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    is_published: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await page_builder_service.list_pages(
        db, page=page, page_size=page_size, keyword=keyword, is_published=is_published
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建搭建页面")
async def create_page(
    payload: PageBuilderCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_CREATE),
) -> dict:
    return resp.success(await page_builder_service.create_page(db, payload), msg="已创建")


@router.get("/{page_id}", response_model=ResponseModel, summary="搭建页面详情")
async def get_page(
    page_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_VIEW),
) -> dict:
    return resp.success(await page_builder_service.get_page(db, page_id))


@router.put("/{page_id}", response_model=ResponseModel, summary="更新搭建页面")
async def update_page(
    page_id: int,
    payload: PageBuilderUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_EDIT),
) -> dict:
    return resp.success(await page_builder_service.update_page(db, page_id, payload), msg="已保存")


@router.delete("/{page_id}", response_model=ResponseModel, summary="删除搭建页面")
async def delete_page(
    page_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_DELETE),
) -> dict:
    await page_builder_service.delete_page(db, page_id)
    return resp.success(None, msg="已删除")


@router.post("/{page_id}/publish", response_model=ResponseModel, summary="发布 / 撤回搭建页面")
async def publish_page(
    page_id: int,
    payload: PageBuilderPublishRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAGE_BUILDER_EDIT),
) -> dict:
    data = await page_builder_service.set_published(db, page_id, payload.is_published)
    return resp.success(data, msg="已发布" if payload.is_published else "已撤回")
