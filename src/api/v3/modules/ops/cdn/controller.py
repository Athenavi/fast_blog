"""ops.cdn 模块路由（T5-11 批次 4：自 astro `admin/cdn` 能力域新建）

::

    GET    /api/v3/ops/cdn/config        读取配置（api_token 脱敏为 has_api_token）
    PUT    /api/v3/ops/cdn/config        保存配置（api_token 留空保持原值）
    POST   /api/v3/ops/cdn/purge         清缓存（真实调用厂商 API）
    POST   /api/v3/ops/cdn/preheat       预热（真实调用厂商 API）

权限码：``module_ops:cdn:view/edit`` + ``module_ops:cdn:execute``（远端动作）。

无独立表：配置持久化在 system_settings 的 ``cdn.config`` 键。

**远端动作**（批次 18 起真实接线，见 ``remote.py``）：``cloudflare`` 走官方 purge_cache API，
``custom`` 调自建网关；``aws_cloudfront`` / ``aliyun_cdn`` / ``tencent_cdn`` 需要厂商签名，
**当前明确报"未实现"**而不是假装成功。任何失败（未配置凭据 / 厂商拒绝 / 网络异常）
都如实返回错误原因。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.cdn.schema import CDNConfigPayload, CDNPurgePayload
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


@router.post("/purge", response_model=ResponseModel, summary="清缓存（远端）")
async def purge_cache(
    payload: CDNPurgePayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CDN_EXECUTE),
) -> dict:
    """真实调用 CDN 厂商接口清缓存；未配置凭据 / provider 未实现都会带原因报错。"""
    return resp.success(await cdn_service.purge(db, payload), msg="已提交清缓存")


@router.post("/preheat", response_model=ResponseModel, summary="预热（远端）")
async def preheat_cache(
    payload: CDNPurgePayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.CDN_EXECUTE),
) -> dict:
    """预热：``custom`` 走自建网关的 preheat_url；``cloudflare`` 无此接口（如实报错）。"""
    return resp.success(await cdn_service.preheat(db, payload), msg="已提交预热")
