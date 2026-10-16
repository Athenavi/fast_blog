"""redirect 模块（T5-11 之后的「多格式迁移」任务 8：SEO 跳转规则）

::

    GET    /api/v3/content/redirect              规则列表
    POST   /api/v3/content/redirect              新建规则
    GET    /api/v3/content/redirect/stats        统计（总数/启用/命中 Top）
    GET    /api/v3/content/redirect/resolve      按路径解析（**公开**，命中即累加 hits）
    POST   /api/v3/content/redirect/bulk         批量导入
    GET    /api/v3/content/redirect/{id}         规则详情
    PUT    /api/v3/content/redirect/{id}         更新规则
    DELETE /api/v3/content/redirect/{id}         删除规则

权限码：``module_analytics:seo:view/edit``（跳转规则属 SEO 能力，复用既有码）。
``resolve`` 供前台 / 反向代理在 404 前查表，因此不鉴权；它只返回路径与状态码，不泄露其它数据。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.redirect.schema import (
    RedirectBatchRequest,
    RedirectCreate,
    RedirectUpdate,
)
from src.api.v3.modules.content.redirect.service import redirect_service

router = APIRouter(prefix="/redirect", tags=["content-redirect"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="跳转规则列表")
async def list_redirects(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
    page: PageDep = None,
    keyword: Optional[str] = Query(default=None, description="按源/目标路径模糊搜索"),
    is_active: Optional[bool] = Query(default=None),
    source: Optional[str] = Query(default=None, description="manual / migration"),
) -> dict:
    items, total = await redirect_service.list_redirects(
        db, page=page.page, page_size=page.page_size, keyword=keyword, is_active=is_active, source=source
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.post("", response_model=ResponseModel, summary="新建跳转规则")
async def create_redirect(
    payload: RedirectCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    return resp.success(
        await redirect_service.create_redirect(
            db, payload.model_dump(exclude_unset=True), user_id=getattr(current, "id", None)
        ),
        msg="已创建",
    )


@router.get("/stats", response_model=ResponseModel, summary="跳转规则统计")
async def redirect_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
) -> dict:
    return resp.success(await redirect_service.stats(db))


@router.get("/resolve", response_model=ResponseModel, summary="按路径解析跳转（公开）")
async def resolve_redirect(
    db: DBSession,
    path: str = Query(..., min_length=1, max_length=500, description="站点内路径或完整 URL"),
) -> dict:
    """**无需鉴权**：命中即返回目标与状态码，并把该规则的 ``hits`` 真实 +1"""
    return resp.success(await redirect_service.resolve_path(db, path))


@router.post("/bulk", response_model=ResponseModel, summary="批量导入跳转规则")
async def bulk_import_redirects(
    payload: RedirectBatchRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    result = await redirect_service.bulk_import(
        db,
        [item.model_dump(exclude_unset=True) for item in payload.items],
        user_id=getattr(current, "id", None),
        overwrite=payload.overwrite,
        source="manual",
        source_reference="bulk-import",
    )
    return resp.success(result, msg=f"新增 {result['created']} / 更新 {result['updated']} / 跳过 {result['skipped']}")


@router.get("/{redirect_id}", response_model=ResponseModel, summary="跳转规则详情")
async def get_redirect(
    redirect_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_VIEW),
) -> dict:
    return resp.success(await redirect_service.get_redirect(db, redirect_id))


@router.put("/{redirect_id}", response_model=ResponseModel, summary="更新跳转规则")
async def update_redirect(
    redirect_id: int,
    payload: RedirectUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    return resp.success(
        await redirect_service.update_redirect(
            db, redirect_id, payload.model_dump(exclude_unset=True)
        ),
        msg="已保存",
    )


@router.delete("/{redirect_id}", response_model=ResponseModel, summary="删除跳转规则")
async def delete_redirect(
    redirect_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SEO_EDIT),
) -> dict:
    await redirect_service.delete_redirect(db, redirect_id)
    return resp.success(None, msg="已删除")
