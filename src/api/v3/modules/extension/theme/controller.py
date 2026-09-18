"""theme 模块路由

**公开（无鉴权，前台注入主题样式/配置）**::

    GET /api/v3/extension/theme/public/css      当前主题 CSS
    GET /api/v3/extension/theme/public/config   当前主题公开配置

**管理端（需权限码）**::

    GET /api/v3/extension/theme/active           当前主题信息
    GET /api/v3/extension/theme/active/config    当前主题配置
    PUT /api/v3/extension/theme/active/config    保存当前主题配置
    GET /api/v3/extension/theme/active/schema    配置 schema 与可用槽位
    GET /api/v3/extension/theme/active/contract  主题契约

权限码：``theme:view`` / ``theme:customize``
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.extension.theme.schema import ThemeConfigUpdate
from src.api.v3.modules.extension.theme.service import theme_ops_service

router = APIRouter(prefix="/theme", tags=["extension-theme"], route_class=OperationLogRoute)


# ─────────────────────────── 公开（无鉴权）───────────────────────────
@router.get("/public/css", response_model=ResponseModel, summary="当前主题 CSS（无需鉴权）")
async def public_theme_css() -> dict:
    return resp.success(await theme_ops_service.active_css())


@router.get("/public/config", response_model=ResponseModel, summary="当前主题公开配置（无需鉴权）")
async def public_theme_config() -> dict:
    return resp.success(await theme_ops_service.active_config())


# ─────────────────────────── 管理端 ───────────────────────────
@router.get("/active", response_model=ResponseModel, summary="当前主题信息")
async def active_theme(
    _current: CurrentUser,
    _perm=AuthControl("theme:view"),
) -> dict:
    return resp.success(await theme_ops_service.active_theme())


@router.get("/active/config", response_model=ResponseModel, summary="当前主题配置")
async def active_theme_config(
    _current: CurrentUser,
    _perm=AuthControl("theme:view"),
) -> dict:
    return resp.success(await theme_ops_service.active_config())


@router.put("/active/config", response_model=ResponseModel, summary="保存当前主题配置")
async def update_theme_config(
    payload: ThemeConfigUpdate,
    _current: CurrentUser,
    _perm=AuthControl("theme:customize"),
) -> dict:
    data = await theme_ops_service.update_config(
        settings=payload.settings, component_slots=payload.component_slots
    )
    return resp.success(data, msg="已保存")


@router.get("/active/schema", response_model=ResponseModel, summary="主题配置 schema 与槽位")
async def active_theme_schema(
    _current: CurrentUser,
    _perm=AuthControl("theme:view"),
) -> dict:
    return resp.success(await theme_ops_service.active_schema())


@router.get("/active/contract", response_model=ResponseModel, summary="主题契约")
async def active_theme_contract(
    _current: CurrentUser,
    _perm=AuthControl("theme:view"),
) -> dict:
    return resp.success(await theme_ops_service.active_contract())
