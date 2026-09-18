"""auth 模块路由

路径：``/api/v3/system/auth/{login,logout,refresh,me,status}``

约定：access token 有效期 1 小时、refresh token 30 天（与 v2 的 cookie 策略一致）；
httponly + samesite=strict，HTTPS 环境下自动加 secure。
"""

from fastapi import APIRouter, Request, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.security import clear_auth_cookies, extract_token, set_auth_cookies
from src.api.v3.modules.system.auth.schema import (
    CurrentUserOut,
    LoginRequest,
    LoginStatusOut,
    RefreshRequest,
    TokenPayload,
)
from src.api.v3.modules.system.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["system-auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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
