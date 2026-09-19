"""ops.cdn 模块路由（T5-11 批次 4：自 astro `admin/cdn` 能力域新建）

::

    GET    /api/v3/ops/cdn/config        读取配置（api_token 脱敏为 has_api_token）
    PUT    /api/v3/ops/cdn/config        保存配置（api_token 留空保持原值）

权限码：``module_ops:cdn:view/edit``。
无独立表：持久化在 system_settings 的 ``cdn.config`` 键；远端清缓存等动作二期。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.cdn.schema import CDNConfigPayload
from src.api.v3.modules.ops.cdn.service import cdn_service

router = APIRouter(prefix="/cdn", tags=["ops-cdn"], route_class=OperationLogRoute)


@router.get("/config", response_model=ResponseModel, summary="读取 CDN 配置")
async def get_config(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CDN_VIEW),
) -> dict:
    return resp.success(await cdn_service.get_config(db))


@router.put("/config", response_model=ResponseModel, summary="保存 CDN 配置")
async def save_config(
    payload: CDNConfigPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CDN_EDIT),
) -> dict:
    return resp.success(await cdn_service.save_config(db, payload), msg="已保存")
