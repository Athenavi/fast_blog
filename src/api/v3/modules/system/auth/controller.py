"""auth 模块路由

路径：``/api/v3/system/auth/{login,logout,refresh,me,status}``

约定：access token 有效期 1 小时、refresh token 30 天（与 v2 的 cookie 策略一致）；
httponly + samesite=strict，HTTPS 环境下自动加 secure。
"""

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.limits import ip_rate_limit
from src.api.v3.core.security import clear_auth_cookies, extract_token, set_auth_cookies
from src.api.v3.modules.system.auth.schema import (
    CurrentUserOut,
    EmailVerifySendRequest,
    LoginRequest,
    LoginStatusOut,
    RefreshRequest,
    TokenPayload,
    Verify2FARequest,
)
from src.api.v3.modules.system.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["system-auth"])


def _client_ip(request: Request) -> str:
    """客户端 IP（统一实现，见 ``shared.utils.client_ip``）"""
    from shared.utils.client_ip import get_client_ip

    return get_client_ip(request)


@router.post("/login", response_model=ResponseModel, summary="登录")
async def login(payload: LoginRequest, request: Request, response: Response, db: DBSession) -> dict:
    identifier = payload.username or payload.email
    if not identifier or not payload.password:
        raise BadRequestError("缺少用户名或密码")

    data = await auth_service.login(
        db,
        identifier=identifier,
        password=payload.password,
        remember_me=payload.remember_me,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    set_auth_cookies(response, data)

    if data.get("requires_2fa"):
        return resp.success(TokenPayload(**data).model_dump(), msg="需要双因素验证")
    return resp.success(TokenPayload(**data).model_dump(), msg="登录成功")


@router.post("/verify-2fa", response_model=ResponseModel, summary="双因素验证（登录第二步）")
async def verify_2fa(
    payload: Verify2FARequest, request: Request, response: Response, db: DBSession
) -> dict:
    data = await auth_service.verify_2fa(
        db,
        temp_token=payload.temp_token,
        code=payload.code,
        remember_me=payload.remember_me,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    set_auth_cookies(response, data)
    return resp.success(TokenPayload(**data).model_dump(), msg="登录成功")


@router.post(
    "/email/verify/send",
    response_model=ResponseModel,
    summary="发送邮箱验证邮件（匿名，防枚举）",
)
async def send_email_verify(
    payload: EmailVerifySendRequest,
    db: DBSession,
    _rl=Depends(ip_rate_limit("auth.email_verify_send", limit=5, window_seconds=900)),
) -> dict:
    """重发验证邮件。

    **匿名可用**：宽限期过后登录会被拦，此时用户只能用这个入口自救。
    无论邮箱是否存在、是否已验证都返回同一句话（防账号枚举），并按 IP 限流。
    """
    await auth_service.send_email_verification(db, email=payload.email)
    return resp.success(None, msg="如果该邮箱需要验证，验证邮件已发送")


@router.get("/email/verify", summary="完成邮箱验证（邮件链接）")
async def verify_email(db: DBSession, token: str = Query(..., min_length=10, max_length=2048)):
    """浏览器点邮件链接即完成验证；返回一个最小 HTML 结果页。"""
    try:
        await auth_service.verify_email(db, token)
    except Exception:  # noqa: BLE001 - 不给链接探测者任何差异信息
        return HTMLResponse(
            "<meta charset='utf-8'><h3>验证失败：链接无效或已过期</h3>", status_code=400
        )
    return HTMLResponse("<meta charset='utf-8'><h3>邮箱验证成功，可以返回应用继续使用。</h3>")


@router.post("/refresh", response_model=ResponseModel, summary="刷新令牌")
async def refresh(payload: RefreshRequest, request: Request, response: Response) -> dict:
    token = payload.refresh_token or request.cookies.get("refresh_token")
    data = await auth_service.refresh(token)
    set_auth_cookies(response, data)
    return resp.success(TokenPayload(**data).model_dump(), msg="令牌已刷新")


@router.post("/logout", response_model=ResponseModel, summary="登出")
async def logout(request: Request, response: Response, user: CurrentUser) -> dict:
    await auth_service.logout(extract_token(request), user)
    clear_auth_cookies(response)
    return resp.success(None, msg="已登出")


@router.get("/me", response_model=ResponseModel, summary="当前登录用户信息")
async def me(db: DBSession, user: CurrentUser) -> dict:
    info = await auth_service.build_current_user(db, user)
    return resp.success(CurrentUserOut(**info).model_dump())


@router.get("/status", response_model=ResponseModel, summary="登录状态")
async def status(user: CurrentUser) -> dict:
    return resp.success(LoginStatusOut(logged_in=True, user_id=user.id).model_dump())
