"""quota 模块路由（站点配额：读取 / 校验 / 更新）

::

    GET  /api/v3/system/quota/{site_id}            读取配额 + 用量（需 site:view）
    POST /api/v3/system/quota/{site_id}/check      校验追加后是否超配额（需 site:view）
    PUT  /api/v3/system/quota/{site_id}            更新配额（需 site:edit）

配额落 ``sites.settings``（Text 列里 JSON 对象的 ``quota`` 键）。用量按真表统计：
``users`` 取 ``site_users``；``articles`` / ``media`` / ``storage_mb`` 因相关表没有
``site_id`` 列，改用「站点成员」口径（返回体 ``usage_scope`` 有说明）。
"""

from typing import Any, Dict

from fastapi import APIRouter, Body

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.quota.schema import QuotaCheckRequest
from src.api.v3.modules.system.quota.service import site_quota_service

router = APIRouter(prefix="/quota", tags=["system-quota"], route_class=OperationLogRoute)


@router.get("/{site_id}", response_model=ResponseModel, summary="读取站点配额与用量")
async def get_site_quota(
    site_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_VIEW),
) -> dict:
    return resp.success(await site_quota_service.get(db, site_id))


@router.post("/{site_id}/check", response_model=ResponseModel, summary="校验配额是否充足")
async def check_site_quota(
    site_id: int,
    payload: QuotaCheckRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SITE_VIEW),
) -> dict:
    return resp.success(
        await site_quota_service.check(
            db, site_id, payload.resource_type, payload.requested_amount
        )
    )


@router.put("/{site_id}", response_model=ResponseModel, summary="更新站点配额")
async def update_site_quota(
    site_id: int,
    db: DBSession,
    _current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受已知配额键；未知键与非法值会被明确拒绝（不是静默忽略）",
        examples=[{"articles": 20000, "storage_mb": None}],
    ),
    _perm=AuthControl(codes.SITE_EDIT),
) -> dict:
    """收**原始 dict** 而不是 pydantic 模型：模型的默认行为会静默丢弃未知字段，
    那样 service 里的「未知键校验」就成了死代码（accessibility 模块真实踩过这个坑）。
    """
    return resp.success(await site_quota_service.update(db, site_id, payload), msg="已保存")
