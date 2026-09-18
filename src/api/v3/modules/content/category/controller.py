"""category 模块路由

RESTful 主路径 + FastApiAdmin 兼容别名::

    GET    /api/v3/content/category               分类列表
    GET    /api/v3/content/category/tree          分类树
    GET    /api/v3/content/category/public        公开分类（无鉴权，供博客前台）
    POST   /api/v3/content/category               新建分类
    DELETE /api/v3/content/category/delete        [兼容] 删除
    GET    /api/v3/content/category/{category_id} 分类详情
    PUT    /api/v3/content/category/{category_id} 更新分类
    DELETE /api/v3/content/category/{category_id} 删除分类

别名：``/list``、``/create``、``/detail/{id}``、``/update/{id}``、``/delete``

权限码：``category:view`` / ``category:create`` / ``category:edit`` / ``category:delete``
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.category.schema import CategoryCreate, CategoryUpdate
from src.api.v3.modules.content.category.service import category_service

router = APIRouter(prefix="/category", tags=["content-category"], route_class=OperationLogRoute)


# ─────────────────────────── 公开读（无鉴权）───────────────────────────
@router.get("/public", response_model=ResponseModel, summary="公开分类列表（无需鉴权）")
async def public_categories(db: DBSession) -> dict:
    categories = await category_service.list_categories(db, is_visible=True)
    return resp.success_page(categories, len(categories), 1, len(categories) or 1)


@router.get("/public/tree", response_model=ResponseModel, summary="公开分类树（无需鉴权）")
async def public_category_tree(db: DBSession) -> dict:
    return resp.success(await category_service.tree(db, is_visible=True))


# ─────────────────────────── 列表 / 树 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="分类列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 分类列表",
)
async def list_categories(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:view"),
    is_visible: Optional[bool] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items = await category_service.list_categories(db, is_visible=is_visible, keyword=keyword)
    return resp.success_page(items, len(items), 1, len(items) or 1)


@router.get("/tree", response_model=ResponseModel, summary="分类树")
async def category_tree(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:view"),
    is_visible: Optional[bool] = Query(default=None),
) -> dict:
    return resp.success(await category_service.tree(db, is_visible=is_visible))


# ─────────────────────────── 新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建分类")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建分类",
)
async def create_category(
    payload: CategoryCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:create"),
) -> dict:
    return resp.success(await category_service.create_category(db, payload), msg="创建成功")


# ─────────────────────────── 兼容删除（静态路径必须先注册）───────────
@router.delete(
    "/delete",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 删除分类",
)
async def delete_category_compat(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:delete"),
    category_id: int = Query(description="待删除分类 id"),
) -> dict:
    await category_service.delete_category(db, category_id)
    return resp.success(None, msg="已删除")


# ─────────────────────────── 详情 / 更新 / 删除 ───────────────────────────
@router.get("/{category_id}", response_model=ResponseModel, summary="分类详情")
@router.get(
    "/detail/{category_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 分类详情",
)
async def get_category(
    category_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:view"),
) -> dict:
    category = await category_service.get_category(db, category_id)
    from src.api.v3.modules.content.category.schema import CategoryOut

    return resp.success(CategoryOut.model_validate(category).model_dump())


@router.put("/{category_id}", response_model=ResponseModel, summary="更新分类")
@router.put(
    "/update/{category_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新分类",
)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:edit"),
) -> dict:
    return resp.success(await category_service.update_category(db, category_id, payload), msg="更新成功")


@router.delete("/{category_id}", response_model=ResponseModel, summary="删除分类")
async def delete_category(
    category_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("category:delete"),
) -> dict:
    await category_service.delete_category(db, category_id)
    return resp.success(None, msg="已删除")
