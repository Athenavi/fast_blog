"""
V3 主题管理 API

权限要求:
  GET    /themes               → theme:view
  POST   /themes/{slug}/activate  → theme:activate
  PUT    /themes/{slug}/config    → theme:customize
  DELETE /themes/{slug}           → theme:delete
"""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission
from shared.services.plugins.plugin_manager.core import plugin_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-themes"])


@router.get("/themes", summary="主题列表")
async def list_themes(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("theme:view")),
):
    installed = []
    for plugin in plugin_manager.plugins.values():
        info = plugin.get_info()
        if info.get("type") == "theme":
            installed.append(info)
    return ApiResponse(success=True, data={"themes": installed})


@router.post("/themes/{slug}/activate", summary="激活主题")
async def activate_theme(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("theme:activate")),
):
    success = plugin_manager.activate_plugin(slug)
    if not success:
        return ApiResponse(success=False, error="激活失败，请确认主题存在")
    return ApiResponse(success=True, message=f"主题 {slug} 已激活")


@router.get("/themes/{slug}/config", summary="主题配置")
async def get_theme_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("theme:customize")),
):
    plugin = plugin_manager.get_plugin(slug)
    if not plugin:
        return ApiResponse(success=False, error="主题不存在")
    return ApiResponse(success=True, data={"config": plugin.get_config()})


@router.put("/themes/{slug}/config", summary="更新主题配置")
async def update_theme_config(
    slug: str,
    config: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("theme:customize")),
):
    plugin_manager.update_plugin_settings(slug, config)
    return ApiResponse(success=True, message="主题配置已更新")


@router.delete("/themes/{slug}", summary="卸载主题")
async def uninstall_theme(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("theme:delete")),
):
    success = plugin_manager.uninstall_plugin(slug)
    if not success:
        return ApiResponse(success=False, error="卸载失败")
    return ApiResponse(success=True, message=f"主题 {slug} 已卸载")
