"""theme 模块业务逻辑

数据源：``PluginManager.get_active_theme_plugin()``（返回 ``ThemePlugin`` 实例）。
所有调用经 ``maybe_await`` 兼容 sync/async 实现。
"""

from typing import Any, Dict, List, Optional

from src.api.v3.common.async_utils import maybe_await
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("theme")


class ThemeOpsService:
    """当前主题与配置"""

    # ------------------------------------------------------------------ 内部
    @staticmethod
    def _manager():
        from shared.services.plugins.plugin_manager.core import plugin_manager

        return plugin_manager

    async def _active_plugin(self):
        manager = self._manager()
        plugin = await maybe_await(manager.get_active_theme_plugin())
        if plugin is None:
            raise NotFoundError("当前没有激活的主题")
        return plugin

    async def _plugin_by_slug(self, slug: str):
        """按 slug 取主题插件（自 v2 ``_get_theme_plugin`` 平移）"""
        manager = self._manager()
        plugin = await maybe_await(manager.get_plugin(slug))
        if plugin is None:
            raise NotFoundError(f"主题未找到: {slug}")
        await maybe_await(plugin.load_metadata())
        manifest = getattr(plugin, "manifest", None)
        if not manifest or getattr(manifest, "category", None) != "theme":
            raise NotFoundError(f"不是主题插件: {slug}")
        return plugin

    @staticmethod
    async def _info_of(plugin) -> dict:
        info = await maybe_await(plugin.get_info())
        if isinstance(info, dict):
            return info
        return {"raw": str(info)}

    # ------------------------------------------------------------------ 查询
    async def active_theme(self) -> dict:
        plugin = await self._active_plugin()
        return await self._info_of(plugin)

    async def active_config(self) -> dict:
        plugin = await self._active_plugin()
        info = await self._info_of(plugin)
        settings = info.get("settings") or {}
        if not settings and hasattr(plugin, "get_theme_settings"):
            settings = await maybe_await(plugin.get_theme_settings()) or {}

        slots: Dict[str, Any] = {}
        if hasattr(plugin, "get_component_slots"):
            slots = await maybe_await(plugin.get_component_slots()) or {}

        # L1 声明式页面：从 theme.json 的 templates 读出区块描述并做白名单校验。
        #
        # 这是"主题热插拔"的关键 —— 页面结构变成随 bootstrap 下发的**纯数据**，
        # 前端用内置渲染器解释执行；改 theme.json 刷新即生效，**不需要重新构建**。
        #
        # 注意取值来源：`_info_of()` 走 `get_info()`，它**不含** templates
        # （只给 id/name/slug/settings/capabilities 等），所以这里必须单独读配置。
        from src.api.v3.modules.extension.theme.blocks import normalize_templates

        config: Dict[str, Any] = {}
        if hasattr(plugin, "get_theme_config"):
            config = await maybe_await(plugin.get_theme_config()) or {}

        templates, block_warnings = normalize_templates(config.get("templates"))
        for warning in block_warnings:
            # 跳过而非报错：主题可能面向更新的版本，少一个区块远比整页 500 好
            logger.warning("[theme] %s 的区块被跳过：%s", info.get("slug"), warning)

        return {
            "slug": info.get("slug"),
            "settings": settings,
            "component_slots": slots,
            "settings_schema": info.get("settings_schema"),
            "templates": templates,
        }

    async def active_schema(self) -> dict:
        plugin = await self._active_plugin()
        info = await self._info_of(plugin)
        schema: Dict[str, Any] = info.get("settings_schema") or {}
        if not schema and hasattr(plugin, "get_settings_schema"):
            schema = await maybe_await(plugin.get_settings_schema()) or {}

        slots: List[str] = []
        if hasattr(plugin, "get_component_slots"):
            raw_slots = await maybe_await(plugin.get_component_slots()) or {}
            if isinstance(raw_slots, dict):
                slots = sorted(raw_slots.keys())
        return {"slug": info.get("slug"), "settings_schema": schema, "slots": slots}

    async def active_contract(self) -> dict:
        plugin = await self._active_plugin()
        contract: Dict[str, Any] = {}
        if hasattr(plugin, "get_theme_contract"):
            contract = await maybe_await(plugin.get_theme_contract()) or {}
        return {"contract": contract}

    async def active_css(self) -> dict:
        plugin = await self._active_plugin()
        css = ""
        if hasattr(plugin, "get_css_content"):
            css = await maybe_await(plugin.get_css_content()) or ""
        info = await self._info_of(plugin)

        # 主题设置 → CSS 变量块。
        #
        # 这一步是"配置真的生效"的关键：主题的 styles.css 只引用 `--color-primary`
        # 这类变量、不写死颜色，改后台配置就能立即改变外观。缺了它，
        # theme.json 里的 settings 就只是摆设（改了没反应的假实现）。
        from src.api.v3.modules.extension.theme.variables import render_theme_variables

        settings = info.get("settings") or {}
        if not settings and hasattr(plugin, "get_theme_settings"):
            settings = await maybe_await(plugin.get_theme_settings()) or {}
        variables = render_theme_variables(settings)

        return {
            "slug": info.get("slug"),
            "css": css,
            "variables": variables,
            "length": len(css) + len(variables),
        }

    # ------------------------------------------------------------------ 变更
    async def update_config(
        self, *, settings: Dict[str, Any], component_slots: Optional[Dict[str, Any]] = None
    ) -> dict:
        plugin = await self._active_plugin()

        update = getattr(plugin, "update_theme_settings", None)
        if update is None:
            raise BadRequestError("当前主题实现不支持保存配置")
        ok = await maybe_await(update(settings or {}))
        if not ok:
            raise BadRequestError("主题配置保存失败")

        if component_slots is not None:
            setter = getattr(plugin, "update_component_slots", None)
            if setter is None:
                # 不猜测未确认的接口：明确忽略并留下日志，而不是静默丢弃
                logger.warning("当前主题实现没有 update_component_slots，component_slots 已忽略")
            else:
                await maybe_await(setter(component_slots))

        return await self.active_config()

    # ------------------------------------------------------------------ 按 slug 配置
    # 自 v2 ``GET/PUT /api/v2/themes/{slug}/config`` 平移（T5-10）：
    # 主题配置页配置的是**各自 slug**（不一定是当前激活主题），
    # 不一定是激活主题，因此与 ``active_config`` 分离。
    async def theme_config(self, slug: str) -> dict:
        plugin = await self._plugin_by_slug(slug)

        config: Dict[str, Any] = {}
        if hasattr(plugin, "get_theme_config"):
            config = await maybe_await(plugin.get_theme_config()) or {}
        settings = getattr(plugin, "settings", None) or config.get("settings", {})
        metadata = getattr(plugin, "metadata", None) or {}
        contract: Dict[str, Any] = {}
        if hasattr(plugin, "get_theme_contract"):
            contract = await maybe_await(plugin.get_theme_contract()) or {}

        return {
            "slug": slug,
            "settings": settings,
            "settings_schema": metadata.get("settings_schema", {}),
            "supports": config.get("supports", []),
            "contract": contract,
        }

    async def update_theme_config(
        self, slug: str, *, settings: Dict[str, Any], component_slots: Optional[Dict[str, Any]] = None
    ) -> dict:
        """保存按 slug 的主题配置（写法与 v2 一致：槽位落 ``settings._componentSlots``）"""
        plugin = await self._plugin_by_slug(slug)

        update = getattr(plugin, "update_theme_settings", None)
        if update is not None:
            ok = await maybe_await(update(settings or {}))
            if not ok:
                raise BadRequestError("主题配置保存失败")
        else:
            plugin.settings.update(settings or {})
            await maybe_await(plugin.save_settings())

        if component_slots and isinstance(component_slots, dict):
            plugin.settings["_componentSlots"] = component_slots
            await maybe_await(plugin.save_settings())

        slots: Dict[str, Any] = component_slots or {}
        if hasattr(plugin, "get_component_slots"):
            slots = await maybe_await(plugin.get_component_slots()) or slots

        return {"slug": slug, "settings": plugin.settings, "componentSlots": slots}


theme_ops_service = ThemeOpsService()
