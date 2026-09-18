"""mobile/auth 路由

::

    POST /api/v3/mobile/auth/login      登录（无需鉴权）
    POST /api/v3/mobile/auth/register   注册（无需鉴权）

响应统一为 ``{code, msg, data, pagination}``；登录同时下发 ``access_token`` /
``refresh_token`` cookie（与 system/auth 一致）。
"""

from fastapi import APIRouter, Request, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.security import set_auth_cookies
from src.api.v3.modules.mobile.auth.schema import MobileLoginRequest, MobileRegisterRequest
from src.api.v3.modules.mobile.auth.service import mobile_auth_service

router = APIRouter(prefix="/auth", tags=["mobile-auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=ResponseModel, summary="移动端登录")
async def mobile_login(
    payload: MobileLoginRequest,
    request: Request,
    response: Response,
    db: DBSession,
) -> dict:
    identifier = payload.username or payload.email
    if not identifier or not payload.password:
        raise BadRequestError("缺少用户名或密码")

    data = await mobile_auth_service.login(
        db,
        identifier=identifier,
        password=payload.password,
        remember_me=payload.remember_me,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    set_auth_cookies(response, data)
    return resp.success(data, msg="需要双因素验证" if data.get("requires_2fa") else "登录成功")


@router.post("/register", response_model=ResponseModel, summary="移动端注册")
async def mobile_register(
    payload: MobileRegisterRequest,
    request: Request,
    response: Response,
    db: DBSession,
) -> dict:
    data = await mobile_auth_service.register(
        db,
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    set_auth_cookies(response, data)
    return resp.success(data, msg="注册成功")
