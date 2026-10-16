"""api_token 模块路由（对外 API 令牌）

::

    GET    /api/v3/system/api-token          列出令牌（普通用户仅自己的；管理员可见全部）
    POST   /api/v3/system/api-token          签发令牌（**明文仅本次返回**）
    DELETE /api/v3/system/api-token/{id}     撤销令牌（软删，保留审计线索）

权限码：``module_system:apitoken:{view,create,delete}``。

令牌的**实际**权限 = ``scopes ∩ 归属用户当前权限码``（见 ``core/permission/control.py``），
因此用户被降权/撤销角色后，其令牌对应权限立即同步失效；签发时也会校验
``scopes`` 不得超出发起者自身权限（见 service）。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.api_token.schema import ApiTokenCreate
from src.api.v3.modules.system.api_token.service import ApiTokenService

router = APIRouter(
    prefix="/api-token",
    tags=["system-api-token"],
    route_class=OperationLogRoute,
)

api_token_service = ApiTokenService()


@router.get("", response_model=ResponseModel, summary="令牌列表")
async def list_tokens(
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.APITOKEN_VIEW),
) -> dict:
    items, is_admin_view = await api_token_service.list_tokens(db, user=current)
    return resp.success({"items": items, "is_admin_view": is_admin_view})


@router.post("", response_model=ResponseModel, summary="签发令牌（明文仅本次返回）")
async def create_token(
    payload: ApiTokenCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.APITOKEN_CREATE),
) -> dict:
    data = await api_token_service.create_token(
        db,
        user=current,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )
    return resp.success(data, msg="令牌已签发：明文只显示这一次，请立即保存")


@router.delete("/{token_id}", response_model=ResponseModel, summary="撤销令牌")
async def revoke_token(
    token_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.APITOKEN_DELETE),
) -> dict:
    await api_token_service.revoke_token(db, user=current, token_id=token_id)
    return resp.success(None, msg="令牌已撤销")
