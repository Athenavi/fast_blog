"""site 模块路由（T5-11 批次 4：自 astro `admin/multisite` 能力域新建）

::

    GET    /api/v3/system/site                站点列表
    POST   /api/v3/system/site                新建站点
    PUT    /api/v3/system/site/{site_id}      更新站点（slug 不可改）
    DELETE /api/v3/system/site/{site_id}      删除站点（默认站点不可删）

权限码：``module_system:site:view/create/edit/delete``。
slug 唯一且创建后锁定；domain 唯一；``is_default`` 全站唯一。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.site.schema import SiteCreate, SiteUpdate
from src.api.v3.modules.system.site.service import site_service

router = APIRouter(prefix="/site", tags=["system-site"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="站点列表")
async def list_sites(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await site_service.list_sites(
        db, page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建站点")
async def create_site(
    payload: SiteCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_CREATE),
) -> dict:
    return resp.success(await site_service.create_site(db, payload), msg="已创建")


@router.put("/{site_id}", response_model=ResponseModel, summary="更新站点")
async def update_site(
    site_id: int,
    payload: SiteUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    return resp.success(await site_service.update_site(db, site_id, payload), msg="已保存")


@router.delete("/{site_id}", response_model=ResponseModel, summary="删除站点")
async def delete_site(
    site_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_DELETE),
) -> dict:
    await site_service.delete_site(db, site_id)
    return resp.success(None, msg="已删除")
