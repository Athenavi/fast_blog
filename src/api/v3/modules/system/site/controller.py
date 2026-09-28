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
from src.api.v3.modules.system.site.multisite_service import multisite_service
from src.api.v3.modules.system.site.schema import (
    SiteCreate,
    SiteDomainsUpdate,
    SiteMemberCreate,
    SiteUpdate,
)
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


# ─────────────────────────── 多站点：域名解析 + 用户归属 ───────────────────────────
@router.get("/resolve", response_model=ResponseModel, summary="按域名解析站点（公开）")
async def resolve_site_by_domain(
    db: DBSession,
    domain: str = Query(..., min_length=1, max_length=255, description="Host，如 blog.example.com"),
) -> dict:
    """**无需鉴权**：前台 SSR / 反向代理按 Host 定位站点配置

    匹配顺序：主域名精确 → 附加域名 → 回退默认站点（回退时 ``matched=false``）。
    """
    return resp.success(await multisite_service.resolve_by_domain(db, domain))


@router.get("/mine", response_model=ResponseModel, summary="当前用户所属站点")
async def my_sites(db: DBSession, current: CurrentUser) -> dict:
    return resp.success(await multisite_service.user_sites(db, getattr(current, "id")))


@router.put("/{site_id}/domains", response_model=ResponseModel, summary="设置站点域名（主域名 + 附加域名）")
async def update_site_domains(
    site_id: int,
    payload: SiteDomainsUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    return resp.success(
        await multisite_service.set_domains(
            db, site_id, domain=payload.domain, additional_domains=payload.additional_domains
        ),
        msg="域名已更新",
    )


@router.post("/{site_id}/default", response_model=ResponseModel, summary="设为默认站点")
async def set_default_site(
    site_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    return resp.success(await multisite_service.set_default(db, site_id), msg="已设为默认站点")


@router.get("/{site_id}/members", response_model=ResponseModel, summary="站点成员列表")
async def list_site_members(
    site_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await multisite_service.list_members(db, site_id, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)


@router.post("/{site_id}/members", response_model=ResponseModel, summary="添加 / 更新站点成员")
async def add_site_member(
    site_id: int,
    payload: SiteMemberCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    data = await multisite_service.add_member(
        db, site_id, user_id=payload.user_id, role=payload.role, is_active=payload.is_active
    )
    return resp.success(data, msg="已加入站点" if data["created"] else "成员信息已更新")


@router.delete("/{site_id}/members/{user_id}", response_model=ResponseModel, summary="移除站点成员")
async def remove_site_member(
    site_id: int,
    user_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    await multisite_service.remove_member(db, site_id, user_id)
    return resp.success(None, msg="已移除")
