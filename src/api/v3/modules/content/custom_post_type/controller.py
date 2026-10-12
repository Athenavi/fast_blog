"""custom_post_type 模块路由（T5-11 批次 1：自 astro `admin/custom-post-types` 能力域新建）

::

    GET    /api/v3/content/custom-post-type                    类型列表
    POST   /api/v3/content/custom-post-type                    新建类型
    PUT    /api/v3/content/custom-post-type/{type_id}          更新类型
    DELETE /api/v3/content/custom-post-type/{type_id}          删除类型

权限码：``module_content:custom_post_type:view/create/edit/delete``。
slug 唯一；更新时 slug 不可改（内容数据已按它组织）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.custom_post_type.schema import (
    CustomFieldValuesUpdate,
    CustomPostTypeCreate,
    CustomPostTypeUpdate,
)
from src.api.v3.modules.content.custom_post_type.service import custom_post_type_service

router = APIRouter(
    prefix="/custom-post-type", tags=["content-custom-post-type"], route_class=OperationLogRoute
)


@router.get("", response_model=ResponseModel, summary="内容类型列表")
async def list_types(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await custom_post_type_service.list_types(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建内容类型")
async def create_type(
    payload: CustomPostTypeCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_CREATE),
) -> dict:
    return resp.success(await custom_post_type_service.create_type(db, payload), msg="已创建")


@router.put("/{type_id}", response_model=ResponseModel, summary="更新内容类型")
async def update_type(
    type_id: int,
    payload: CustomPostTypeUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_EDIT),
) -> dict:
    return resp.success(await custom_post_type_service.update_type(db, type_id, payload), msg="已保存")


@router.delete("/{type_id}", response_model=ResponseModel, summary="删除内容类型")
async def delete_type(
    type_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_DELETE),
) -> dict:
    await custom_post_type_service.delete_type(db, type_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 字段值（EAV） ───────────────────────────
@router.get("/{type_id}/values/{content_id}", response_model=ResponseModel, summary="读取字段值")
async def get_field_values(
    type_id: int,
    content_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_VIEW),
) -> dict:
    """按类型定义返回字段值（未填字段为 ``null``），便于前端直接渲染表单。"""
    return resp.success(await custom_post_type_service.get_values(db, type_id, content_id))


@router.put(
    "/{type_id}/values/{content_id}",
    response_model=ResponseModel,
    summary="写入字段值（按定义校验）",
)
async def set_field_values(
    type_id: int,
    content_id: int,
    payload: CustomFieldValuesUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CPT_EDIT),
) -> dict:
    """按类型定义校验并 upsert 字段值；未定义的 key、类型不符一律 400（不静默丢弃）。"""
    result = await custom_post_type_service.set_values(
        db, type_id, content_id, payload.values, user_id=getattr(_current, "id", None)
    )
    return resp.success(result, msg="字段值已保存")
