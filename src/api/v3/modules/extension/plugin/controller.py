"""plugin 模块路由

::

    GET    /api/v3/extension/plugin                  插件列表
    GET    /api/v3/extension/plugin/scan             扫描新插件（静态路径，必须先注册）
    GET    /api/v3/extension/plugin/{slug}           插件详情
    GET    /api/v3/extension/plugin/{slug}/settings  插件配置
    PUT    /api/v3/extension/plugin/{slug}/settings  保存插件配置
    POST   /api/v3/extension/plugin/{slug}/install   安装（需 confirm=true）
    POST   /api/v3/extension/plugin/{slug}/activate  激活（需 confirm=true）
    POST   /api/v3/extension/plugin/{slug}/deactivate 停用（需 confirm=true）
    DELETE /api/v3/extension/plugin/{slug}           卸载（需 confirm=true）

权限码：``plugin:view`` / ``plugin:configure`` / ``plugin:install`` /
``plugin:activate`` / ``plugin:delete``
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.extension.plugin.schema import PluginSettingsUpdate
from src.api.v3.modules.extension.plugin.service import plugin_ops_service, require_confirm

router = APIRouter(prefix="/plugin", tags=["extension-plugin"], route_class=OperationLogRoute)

CONFIRM_QUERY = Query(
    default=False,
    description="危险操作二次确认：必须显式传 true",
)


# ─────────────────────────── 静态路径优先 ───────────────────────────
@router.get("/scan", response_model=ResponseModel, summary="扫描新插件")
async def scan_plugins(
    _current: CurrentUser,
    _perm=AuthControl("plugin:view"),
) -> dict:
    return resp.success(await plugin_ops_service.scan_new())


# ─────────────────────────── 列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="插件列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 插件列表",
)
async def list_plugins(
    _current: CurrentUser,
    _perm=AuthControl("plugin:view"),
) -> dict:
    items = await plugin_ops_service.list_plugins()
    return resp.success_page(items, len(items), 1, len(items) or 1)


# ─────────────────────────── 详情 / 配置 ───────────────────────────
@router.get("/{slug}", response_model=ResponseModel, summary="插件详情")
@router.get(
    "/detail/{slug}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 插件详情",
)
async def get_plugin(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:view"),
) -> dict:
    return resp.success(await plugin_ops_service.get_plugin(slug))


@router.get("/{slug}/settings", response_model=ResponseModel, summary="插件配置")
async def get_plugin_settings(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:configure"),
) -> dict:
    return resp.success(await plugin_ops_service.plugin_settings(slug))


@router.put("/{slug}/settings", response_model=ResponseModel, summary="保存插件配置")
async def update_plugin_settings(
    slug: str,
    payload: PluginSettingsUpdate,
    _current: CurrentUser,
    _perm=AuthControl("plugin:configure"),
) -> dict:
    return resp.success(await plugin_ops_service.update_settings(slug, payload.settings), msg="已保存")


# ─────────────────────────── 危险操作（需 confirm=true）───────────────────────────
@router.post("/{slug}/install", response_model=ResponseModel, summary="安装插件（需二次确认）")
async def install_plugin(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:install"),
    confirm: bool = CONFIRM_QUERY,
) -> dict:
    require_confirm(confirm, "安装插件")
    return resp.success(await plugin_ops_service.install(slug), msg="安装成功")


@router.post("/{slug}/activate", response_model=ResponseModel, summary="激活插件（需二次确认）")
async def activate_plugin(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:activate"),
    confirm: bool = CONFIRM_QUERY,
) -> dict:
    require_confirm(confirm, "激活插件")
    return resp.success(await plugin_ops_service.activate(slug), msg="已激活")


@router.post("/{slug}/deactivate", response_model=ResponseModel, summary="停用插件（需二次确认）")
async def deactivate_plugin(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:activate"),
    confirm: bool = CONFIRM_QUERY,
) -> dict:
    require_confirm(confirm, "停用插件")
    return resp.success(await plugin_ops_service.deactivate(slug), msg="已停用")


@router.delete("/{slug}", response_model=ResponseModel, summary="卸载插件（需二次确认）")
async def uninstall_plugin(
    slug: str,
    _current: CurrentUser,
    _perm=AuthControl("plugin:delete"),
    confirm: bool = CONFIRM_QUERY,
) -> dict:
    require_confirm(confirm, "卸载插件")
    return resp.success(await plugin_ops_service.uninstall(slug), msg="已卸载")
