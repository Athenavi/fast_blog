"""
V3 插件管理 API

权限要求:
  GET    /plugins              → plugin:view
  POST   /plugins/{slug}/activate   → plugin:activate
  POST   /plugins/{slug}/deactivate → plugin:activate
  GET    /plugins/{slug}/settings   → plugin:configure
  PUT    /plugins/{slug}/settings   → plugin:configure
  DELETE /plugins/{slug}            → plugin:delete
"""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-plugins"])


@router.get("/plugins", summary="插件列表")
async def list_plugins(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:view")),
):
    """获取已安装插件列表"""
    from shared.services.plugins.plugin_manager.core import plugin_manager
    plugins = plugin_manager.get_plugins_info()
    return ApiResponse(success=True, data={"plugins": plugins})


@router.post("/plugins/{slug}/activate", summary="激活插件")
async def activate_plugin(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:activate")),
):
    from shared.services.plugins.plugin_manager.core import plugin_manager
    success = plugin_manager.activate_plugin(slug)
    if not success:
        return ApiResponse(success=False, error="激活失败")
    return ApiResponse(success=True, message=f"插件 {slug} 已激活")


@router.post("/plugins/{slug}/deactivate", summary="停用插件")
async def deactivate_plugin(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:activate")),
):
    from shared.services.plugins.plugin_manager.core import plugin_manager
    success = plugin_manager.deactivate_plugin(slug)
    return ApiResponse(success=True, message=f"插件 {slug} 已停用")


@router.get("/plugins/{slug}/settings", summary="插件设置")
async def get_plugin_settings(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:configure")),
):
    from shared.services.plugins.plugin_manager.core import plugin_manager
    settings = plugin_manager.get_plugin_settings(slug)
    return ApiResponse(success=True, data={"settings": settings})


@router.put("/plugins/{slug}/settings", summary="更新插件设置")
async def update_plugin_settings(
    slug: str,
    settings: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:configure")),
):
    from shared.services.plugins.plugin_manager.core import plugin_manager
    plugin_manager.update_plugin_settings(slug, settings)
    return ApiResponse(success=True, message="设置已更新")


@router.delete("/plugins/{slug}", summary="卸载插件")
async def uninstall_plugin(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("plugin:delete")),
):
    from shared.services.plugins.plugin_manager.core import plugin_manager
    plugin_manager.uninstall_plugin(slug)
    return ApiResponse(success=True, message=f"插件 {slug} 已卸载")
