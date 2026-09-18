"""plugin 模块业务逻辑（薄封装 ``plugin_manager``）

``PluginManager`` 的方法签名在不同版本里可能是 sync 也可能是 async，因此统一用
``_maybe_await`` 兼容两种形态，避免出现"忘记 await 拿到 coroutine"的隐性错误
（v2 的 widgets 端点就踩过这个坑）。
"""

import asyncio
from typing import Any, List

from src.api.v3.common.async_utils import maybe_await as _maybe_await
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("plugin")


def require_confirm(confirm: bool, action: str) -> None:
    """危险操作二次确认（安装 / 激活 / 停用 / 卸载）"""
    if not confirm:
        raise BadRequestError(
            f"{action} 会动态加载或卸载运行中的插件代码，请显式传入 confirm=true 二次确认"
        )


def _normalize(info: Any) -> dict:
    """把 ``BasePlugin.get_info()`` 的返回值统一成 dict"""
    if isinstance(info, dict):
        return info
    to_dict = getattr(info, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return {"raw": str(info)}


class PluginOpsService:
    """插件管理"""

    @staticmethod
    def _manager():
        from shared.services.plugins.plugin_manager.core import plugin_manager

        return plugin_manager

    async def list_plugins(self) -> List[dict]:
        manager = self._manager()
        try:
            await _maybe_await(manager.discover_plugins())
        except Exception:  # noqa: BLE001 - 目录扫描失败不应让列表接口 500
            logger.exception("插件目录扫描失败")

        plugins = await _maybe_await(manager.get_installed_plugins())
        return [_normalize(item) for item in (plugins or [])]

    async def get_plugin(self, slug: str) -> dict:
        plugin = await self._load(slug)
        return _normalize(await _maybe_await(plugin.get_info()))

    async def plugin_settings(self, slug: str) -> dict:
        plugin = await self._load(slug)
        info = _normalize(await _maybe_await(plugin.get_info()))
        return {
            "slug": slug,
            "settings": info.get("settings") or {},
            "settings_schema": info.get("settings_schema"),
        }

    async def _load(self, slug: str):
        manager = self._manager()
        plugin = await _maybe_await(manager.get_plugin(slug))
        if plugin is None:
            raise NotFoundError(f"插件 {slug} 不存在或未加载")
        return plugin

    async def _action(self, slug: str, action: str) -> dict:
        manager = self._manager()
        await self._load(slug)

        method = getattr(manager, f"{action}_plugin", None)
        if method is None:
            raise BadRequestError(f"当前版本不支持 {action} 操作（缺少 PluginManager.{action}_plugin）")

        ok = await _maybe_await(method(slug))
        if not ok:
            raise BadRequestError(f"插件 {slug} {action} 失败")
        return {
            "slug": slug,
            "action": action,
            "success": True,
            "detail": None,
        }

    async def activate(self, slug: str) -> dict:
        return await self._action(slug, "activate")

    async def deactivate(self, slug: str) -> dict:
        return await self._action(slug, "deactivate")

    async def install(self, slug: str) -> dict:
        return await self._action(slug, "install")

    async def uninstall(self, slug: str) -> dict:
        manager = self._manager()
        method = getattr(manager, "uninstall_plugin", None)
        if method is None:
            raise BadRequestError("当前版本不支持卸载操作")
        ok = await _maybe_await(method(slug))
        if not ok:
            raise BadRequestError(f"插件 {slug} 卸载失败")
        return {"slug": slug, "action": "uninstall", "success": True, "detail": None}

    async def update_settings(self, slug: str, settings: dict) -> dict:
        manager = self._manager()
        await self._load(slug)

        method = getattr(manager, "update_plugin_settings", None)
        if method is None:
            raise BadRequestError("当前版本不支持修改插件配置")
        ok = await _maybe_await(method(slug, settings))
        if not ok:
            raise BadRequestError(f"插件 {slug} 配置保存失败")
        return await self.plugin_settings(slug)

    async def scan_new(self) -> dict:
        manager = self._manager()
        method = getattr(manager, "scan_for_new_plugins", None) or getattr(
            manager, "discover_plugins", None
        )
        if method is None:
            return {"new_plugins": [], "count": 0}
        found = await _maybe_await(method()) or []
        names: List[str] = [str(item) for item in found]
        return {"new_plugins": names, "count": len(names)}

    async def execute_action(self, slug: str, action: str, params: dict) -> Any:
        """执行插件自定义动作（自 v2 ``execute_plugin_action`` 平移）

        与 v2 的差异：
        - 插件不存在 / 方法不存在 → 404 / 400（v2 是 200 + success=false）；
        - 保留能力声明校验（方法上的 ``_capability`` → ``plugin.check_capability``）；
        - 插件方法自身的返回值原样透传（含插件级 ``{success: False, error}``），
          由前端包装层统一判定。
        """
        plugin = await self._load(slug)

        method = getattr(plugin, action, None)
        if method is None:
            raise BadRequestError(f"动作 {action} 不存在")

        # 能力声明校验：装饰器 requires_capability 标记在方法上
        action_cap = getattr(method, "_capability", None)
        if action_cap:
            check = getattr(plugin, "check_capability", None)
            if check is not None and not check(action_cap, raise_error=True):
                raise BadRequestError(f"插件 {slug} 缺少能力 {action_cap}")

        # 审计日志：记录插件操作（失败不影响主流程）
        try:
            from shared.services.plugins.plugin_manager.core import plugin_audit_logger

            plugin_audit_logger.log_api_call(
                plugin_slug=slug,
                api_endpoint=action,
                method="ACTION",
                context={"params": params},
            )
        except Exception:  # noqa: BLE001
            pass

        try:
            if asyncio.iscoroutinefunction(method):
                return await method(**params)
            return method(**params)
        except TypeError:
            # 某些插件方法接受单个 dict 参数而非 **kwargs
            if asyncio.iscoroutinefunction(method):
                return await method(params)
            return method(params)


plugin_ops_service = PluginOpsService()
