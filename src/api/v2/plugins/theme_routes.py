"""
主题管理 API 端点（V2�?
主题�?category="theme" 的插件形式存在，同时只能有一个启用�?前端 AdminThemeMarketplace.tsx 调用这些端点�?"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.services.plugins.plugin_manager.core import plugin_manager
from shared.services.plugins.plugin_manager.theme_plugin import ThemePlugin
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.unified_manager import get_db_session as get_async_db

router = APIRouter(tags=["themes"])


def _get_theme_plugins() -> list[ThemePlugin]:
    """获取所�?category='theme' 的插件实�?""
    themes = []
    for plugin in plugin_manager.plugins.values():
        plugin.load_metadata()
        if plugin.manifest and plugin.manifest.category == "theme":
            themes.append(plugin)
    return themes


def _get_theme_plugin(slug: str) -> ThemePlugin:
    """
    根据
    slug
    获取主题插件，不存在则抛�?404
    """
        plugin = plugin_manager.get_plugin(slug)
        if not plugin:
            raise HTTPException(status_code=404, detail=f"主题未找�? {slug}")
        plugin.load_metadata()
        if not plugin.manifest or plugin.manifest.category != "theme":
            raise HTTPException(status_code=404, detail=f"不是主题插件: {slug}")
        return plugin


    # ─── 主题市场 ──────────────────────────

    @router.get("/themes/marketplace")
    @_catch
    async def list_marketplace_themes(
            request: Request,
            category: str = "all",
            current_user: User = Depends(jwt_required),
    ):
        """
    获取主题市场列表
    当前返回本地主题，未来可扩展为从远程市场获取
    """
    themes = _get_theme_plugins()
    result = []
    for theme in themes:
        info = theme.get_info()
        contract = theme.get_theme_contract() if hasattr(theme, 'get_theme_contract') else {}
        result.append({
            "name": info.get("name", ""),
            "slug": info.get("slug", ""),
            "version": info.get("version", ""),
            "description": info.get("description", ""),
            "author": info.get("author", ""),
            "author_url": info.get("author_url", ""),
            "theme_url": info.get("plugin_url", ""),
            "screenshot": info.get("screenshot"),
            "tags": info.get("tags", []),
            "supports": info.get("supports", []),
            "is_installed": info.get("is_installed", False),
            "is_active": info.get("is_active", False),
            "settings_schema": info.get("settings_schema", {}),
            "contract": contract,
        })

    if category != "all":
        result = [t for t in result if category in t.get("tags", [])]

    return ok(data=result)


@router.get("/themes/categories")
@_catch
async def list_theme_categories(
        current_user: User = Depends(jwt_required),
):
    """获取主题分类列表"""
    themes = _get_theme_plugins()
    categories = set()
    categories.add("all")
    for theme in themes:
        info = theme.get_info()
        for tag in info.get("tags", []):
            categories.add(tag)
    return ok(data=sorted(categories))


# ─── 已安装主�?──────────────────────────

@router.get("/themes/installed")
@_catch
async def list_installed_themes(
        current_user: User = Depends(jwt_required),
):
    """获取已安装的主题列表"""
    themes = _get_theme_plugins()
    result = []
    for theme in themes:
        if not theme.installed:
            continue
        info = theme.get_info()
        contract = theme.get_theme_contract() if hasattr(theme, 'get_theme_contract') else {}
        result.append({
            "name": info.get("name", ""),
            "slug": info.get("slug", ""),
            "version": info.get("version", ""),
            "description": info.get("description", ""),
            "author": info.get("author", ""),
            "author_url": info.get("author_url", ""),
            "theme_url": info.get("plugin_url", ""),
            "screenshot": info.get("screenshot"),
            "tags": info.get("tags", []),
            "supports": info.get("supports", []),
            "is_active": info.get("is_active", False),
            "is_installed": info.get("is_installed", False),
            "settings_schema": info.get("settings_schema", {}),
            "contract": contract,
        })
    return ok(data=result)


@router.post("/themes/install")
@_catch
async def install_theme(
        request: Request,
        current_user: User = Depends(jwt_required),
):
    """
    安装主题（通过
    slug
    安装本地主题�?""
    body = await request.json()
    slug = body.get("slug", "")
    if not slug:
        return fail("slug 不能为空")

    plugin = plugin_manager.get_plugin(slug)
    if not plugin:
        return fail(f"主题未找�? {slug}")

    plugin.load_metadata()
    if not plugin.manifest or plugin.manifest.category != "theme":
        return fail(f"不是主题插件: {slug}")

    plugin.install()
    return ok(data={"slug": slug, "name": plugin.name})


@router.post("/themes/{slug}/activate")
@_catch
async def activate_theme(
        slug: str,
        current_user: User = Depends(jwt_required),
):
    """
    激活主...
    激活新主题时自动停用其他已激活的主题（单例逻辑�?PluginManager 中）
    """
    plugin = _get_theme_plugin(slug)

    success = plugin_manager.activate_plugin(slug)
    if not success:
        return fail(f"主题激活失�? {slug}")

    return ok(data={
        "slug": slug,
        "name": plugin.name,
        "is_active": plugin.active,
    })


@router.delete("/themes/{slug}/uninstall")
@_catch
async def uninstall_theme(
        slug: str,
        current_user: User = Depends(jwt_required),
):
    """卸载主题"""
    plugin = _get_theme_plugin(slug)

    success = plugin_manager.uninstall_plugin(slug)
    if not success:
        return fail(f"主题卸载失败: {slug}")

    return ok(data={"slug": slug})


# ─── 主题配置 ──────────────────────────

@router.get("/themes/{slug}/config")
@_catch
async def get_theme_config(
        slug: str,
        current_user: User = Depends(jwt_required),
):
    """获取主题配置（设置�?+ 设置架构�?""
    plugin = _get_theme_plugin(slug)

    config = plugin.get_theme_config() if hasattr(plugin, 'get_theme_config') else {}
    settings = plugin.settings or config.get("settings", {})
    settings_schema = plugin.metadata.get("settings_schema", {})
    contract = plugin.get_theme_contract() if hasattr(plugin, 'get_theme_contract') else {}

    return ok(data={
        "slug": slug,
        "settings": settings,
        "settings_schema": settings_schema,
        "supports": config.get("supports", []),
        "contract": contract,
    })


@router.put("/themes/{slug}/config")
@_catch
async def update_theme_config(
        slug: str,
        request: Request,
        current_user: User = Depends(jwt_required),
):
    """更新主题配置"""
    plugin = _get_theme_plugin(slug)
    body = await request.json()
    new_settings = body.get("settings", body)  # 兼容 {settings: {...}} 和直接传 {...}
    component_slots = body.get("component_slots") or body.get("componentSlots")

    if hasattr(plugin, 'update_theme_settings'):
        success = plugin.update_theme_settings(new_settings)
    else:
        plugin.settings.update(new_settings)
        plugin.save_settings()
        success = True

    # 组件槽位覆盖（持久化�?settings._componentSlots...
    if component_slots and isinstance(component_slots, dict):
        plugin.settings["_componentSlots"] = component_slots
        plugin.save_settings()

    if not success:
        return fail("主题配置保存失败")

    return ok(data={
        "slug": slug,
        "settings": plugin.settings,
        "componentSlots": plugin.get_component_slots() if hasattr(plugin, 'get_component_slots') else component_slots,
    })


# ─── 主题 CSS（前端核心调用）─────────────

@router.get("/themes/active/css")
async def get_active_theme_css():
    """
    返回激活主题的
    CSS
    内容（无认证，公开端点�?""
    active_theme = plugin_manager.get_active_theme_plugin()
    if not active_theme:
        return ok(data={"css": ""})

    if hasattr(active_theme, 'get_css_content'):
        css = active_theme.get_css_content()
    else:
        css_path = active_theme.plugin_dir / "styles.css"
        css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    return ok(data={"css": css})


@router.get("/themes/active/config")
async def get_active_theme_config():
    """返回激活主题的契约与配置（无认证，公开端点，前端据此应用主题）"""
    active_theme = plugin_manager.get_active_theme_plugin()
    if not active_theme:
        return ok(data={"config": {}, "contract": None, "theme": None})

    if hasattr(active_theme, 'get_theme_settings'):
        settings = active_theme.get_theme_settings()
    else:
        settings = active_theme.settings or {}

    contract = active_theme.get_theme_contract() if hasattr(active_theme, 'get_theme_contract') else {}

    return ok(data={
        "config": settings,
        "contract": contract,
        "theme": {
            "slug": active_theme.slug,
            "name": active_theme.name,
        },
    })
