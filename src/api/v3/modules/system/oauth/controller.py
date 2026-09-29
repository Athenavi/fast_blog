"""oauth 模块路由（system 域：OAuth 第三方登录）

::

    GET    /api/v3/system/oauth/providers                 支持的提供方 + 是否已配置（公开）
    GET    /api/v3/system/oauth/bindings                  本人已绑定列表（仅认证）
    GET    /api/v3/system/oauth/{provider}/authorize-url  生成授权跳转信息（仅认证）
    GET    /api/v3/system/oauth/{provider}/callback        回调（公开，第三方重定向）
    POST   /api/v3/system/oauth/{provider}/callback        回调（公开，POST 形态）
    DELETE /api/v3/system/oauth/{provider}                 解绑本人该提供方（仅认证）

**权限码说明**：本模块端点均为**公开**（提供方清单、回调）或**仅认证且只操作本人数据**
（绑定列表 / 解绑 / 生成授权 URL），因此不声明管理权限码。既有 ``system/social`` 模块的
``module_system:social:view`` / ``module_system:social:delete``（``codes.SOCIAL_VIEW`` /
``codes.SOCIAL_DELETE``，常量存在）覆盖**管理端**查看与解除**任意用户**的绑定，职责不重叠。

**写操作审计**：``POST|GET /{provider}/callback`` 会写库并签发登录态，属于"公开登录端点"，
语义与 ``/system/auth/login`` 同类；本模块不修改 ``core/permission/audit.py``（超出本任务写入范围），
如启用 ``strict`` 权限审计，需要把该路径加入 ``EXEMPT_WRITE_ENDPOINTS``（见模块文档的存疑说明）。
"""

from typing import Optional

from fastapi import APIRouter, Query, Request, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession, OptionalUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.core.security import set_auth_cookies
from src.api.v3.modules.system.oauth.schema import CallbackRequest
from src.api.v3.modules.system.oauth.service import oauth_service

router = APIRouter(prefix="/oauth", tags=["system-oauth"], route_class=OperationLogRoute)


def _client_context(request: Request) -> tuple[str, str]:
    """取客户端 IP 与 UA（供登录审计 / 会话记录使用）"""
    ip = request.client.host if request.client else "unknown"
    return ip, request.headers.get("user-agent", "")


# ---------------------------------------------------------------- 公开：提供方清单
@router.get("/providers", response_model=ResponseModel, summary="支持的 OAuth 提供方")
async def list_providers(db: DBSession) -> dict:
    """返回 GitHub / Google / 微信 / QQ / 微博，并标注是否已在 ``oauth.providers`` 配置凭据。"""
    return resp.success(await oauth_service.list_providers(db))


# ---------------------------------------------------------------- 本人：绑定列表
@router.get("/bindings", response_model=ResponseModel, summary="我的第三方账号绑定")
async def list_bindings(db: DBSession, current: CurrentUser) -> dict:
    """仅返回**当前登录用户**已绑定的第三方账号（令牌脱敏）。"""
    return resp.success(await oauth_service.list_bindings(db, current.id))


# ---------------------------------------------------------------- 本人：生成授权 URL
@router.get(
    "/{provider}/authorize-url",
    response_model=ResponseModel,
    summary="生成第三方授权跳转信息",
)
async def authorize_url(
    provider: str,
    db: DBSession,
    _current: CurrentUser,
    redirect_uri: Optional[str] = Query(default=None, description="回调地址；缺省用配置里的值"),
) -> dict:
    """真实拼接授权 URL（含 scope / 带签名的 state / PKCE 的 S256 challenge）。

    凭据（``client_id`` / ``client_secret``）取自 ``system_settings`` 的 ``oauth.providers``；
    **未配置时返回 400 "未配置"**，绝不伪造授权地址。
    """
    return resp.success(
        await oauth_service.build_authorize_url(db, provider, redirect_uri=redirect_uri)
    )


# ---------------------------------------------------------------- 公开：回调（GET）
@router.get("/{provider}/callback", response_model=ResponseModel, summary="第三方登录回调（GET）")
async def callback_get(
    provider: str,
    request: Request,
    response: Response,
    db: DBSession,
    user: OptionalUser,
    code: str = Query(..., description="厂商返回的授权码"),
    state: str = Query(..., description="授权时下发的 state"),
    code_verifier: Optional[str] = Query(default=None, description="PKCE 校验串"),
    remember_me: bool = Query(default=False, description="是否签发 refresh token"),
) -> dict:
    """校验 state → 真实换令牌 → 拉用户信息 → 绑定/建号 → 签发登录态（并写入登录 cookie）。

    第三方通常以 GET 重定向回本地址；已登录用户走"绑定到本人"分支。
    """
    ip, ua = _client_context(request)
    data = await oauth_service.handle_callback(
        db,
        provider,
        code=code,
        state=state,
        code_verifier=code_verifier,
        current_user_id=getattr(user, "id", None),
        remember_me=remember_me,
        ip=ip,
        user_agent=ua,
    )
    set_auth_cookies(response, data)
    return resp.success(data, msg="登录成功")


# ---------------------------------------------------------------- 公开：回调（POST）
@router.post("/{provider}/callback", response_model=ResponseModel, summary="第三方登录回调（POST）")
async def callback_post(
    provider: str,
    payload: CallbackRequest,
    request: Request,
    response: Response,
    db: DBSession,
    user: OptionalUser,
) -> dict:
    """与 GET 回调同实现，用于以 POST 提交 ``code`` / ``state``（如 SPA 前端）。

    校验 state → 真实换令牌 → 拉用户信息 → 绑定/建号 → 签发登录态（并写入登录 cookie）。
    """
    ip, ua = _client_context(request)
    data = await oauth_service.handle_callback(
        db,
        provider,
        code=payload.code,
        state=payload.state,
        code_verifier=payload.code_verifier,
        current_user_id=getattr(user, "id", None),
        remember_me=payload.remember_me,
        ip=ip,
        user_agent=ua,
    )
    set_auth_cookies(response, data)
    return resp.success(data, msg="登录成功")


# ---------------------------------------------------------------- 本人：解绑
@router.delete("/{provider}", response_model=ResponseModel, summary="解绑第三方账号")
async def unbind(provider: str, db: DBSession, current: CurrentUser) -> dict:
    """解除**当前登录用户**对某提供方的绑定（未绑定返回 404）；不影响会话登录态。"""
    return resp.success(await oauth_service.unbind(db, current.id, provider), msg="已解绑")
