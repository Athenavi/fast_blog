"""
主题插件基类

主题是特殊的 category="theme" 插件，同时只能有一个处于激活状态。
ThemePlugin 继承 BasePlugin 并添加主题专属功能：
- CSS 文件加载
- theme.config.js 配置读取
- 截图路径
- 主题配置编辑 API
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from shared.services.plugins.plugin_manager.core import BasePlugin

logger = logging.getLogger(__name__)


class ThemePlugin(BasePlugin):
    """
    主题插件基类
    
    所有主题插件应继承此类而非 BasePlugin。
    自动处理：
    - 主题 CSS 的读取和缓存
    - theme.config.js 的解析
    - 主题配置（颜色、布局、排版）的管理
    """

    def __init__(
            self,
            plugin_id: int,
            name: str,
            slug: str,
            version: str,
            description: str = "",
            author: str = "",
            author_url: str = "",
            plugin_url: str = "",
    ):
        super().__init__(plugin_id, name, slug, version, description, author, author_url, plugin_url)

    # ─── 主题静态资产 ──────────────────────────

    def get_css_path(self) -> Path:
        """获取主题 CSS 文件路径"""
        return self.plugin_dir / "styles.css"

    def get_css_content(self) -> str:
        """读取主题 CSS 内容"""
        css_path = self.get_css_path()
        if css_path.exists():
            return css_path.read_text(encoding="utf-8")
        return ""

    def get_config_js_path(self) -> Path:
        """获取 theme.config.js 文件路径（前端运行时配置）"""
        return self.plugin_dir / "theme.config.js"

    def get_config_js_content(self) -> str:
        """读取 theme.config.js 内容"""
        js_path = self.get_config_js_path()
        if js_path.exists():
            return js_path.read_text(encoding="utf-8")
            # 注意：返回的是原始 JS 源码，前端 eval 或 import 后使用
        return ""

    def get_theme_json_path(self) -> Path:
        """获取 theme.json 文件路径（后端配置数据）"""
        return self.plugin_dir / "theme.json"

    def get_theme_config(self) -> dict:
        """
        读取主题配置（theme.json）
        返回结构：{ settings: { colors: {...}, layout: {...}, typography: {...}, features: {...} }, supports: [...] }
        """
        json_path = self.get_theme_json_path()
        if json_path.exists():
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def get_screenshot_path(self) -> Optional[str]:
        """获取主题截图路径（相对 plugins/<slug>/ 的路径）"""
        metadata = self.get_theme_json_path()
        if metadata.exists():
            try:
                data = json.loads(metadata.read_text(encoding="utf-8"))
                return data.get("screenshot")
            except Exception:
                pass
        # 回退到 metadata.json
        if self.metadata:
            return self.metadata.get("screenshot")
        return None

    # ─── 主题配置管理 ──────────────────────────

    def get_theme_settings(self) -> dict:
        """
        获取主题当前设置
        优先返回已保存的 settings，其次读取 theme.json 默认值
        """
        if self.settings:
            return self.settings
        config = self.get_theme_config()
        return config.get("settings", {})

    def update_theme_settings(self, new_settings: dict) -> bool:
        """
        更新主题设置并持久化
        
        Args:
            new_settings: 新的设置字典
            
        Returns:
            是否成功
        """
        try:
            self.settings.update(new_settings)
            self.save_settings()
            return True
        except Exception as e:
            logger.error("[ThemePlugin] Failed to save settings for %s: %s", self.name, e)
            return False

    def get_settings_schema(self) -> dict:
        """
        获取设置架构（用于前端动态渲染配置表单）
        优先读取 theme.json 中的 settings_schema，其次 metadata.json
        """
        config = self.get_theme_config()
        schema = config.get("settings_schema", {})
        if not schema and self.metadata:
            schema = self.metadata.get("settings_schema", {})
        return schema

    def get_component_slots(self) -> dict:
        """
        获取组件槽位选择（componentSlots）：
        已保存的覆盖（settings._componentSlots）优先，其次 theme.json 默认。
        """
        defaults = self.get_theme_config().get("componentSlots", {})
        overrides = (self.settings or {}).get("_componentSlots", {})
        if not isinstance(overrides, dict):
            overrides = {}
        merged = dict(defaults)
        merged.update({k: v for k, v in overrides.items() if v})
        return merged

    def get_theme_contract(self) -> dict:
        """
        返回主题契约（标准结构，供后端下发 / 前端动态应用）

        契约包含：metadata、默认设置、设置表单 schema、布局契约、
        组件契约、能力列表、截图、CSS/配置地址。
        前端据此动态渲染配置面板、应用布局/组件/样式。
        """
        config = self.get_theme_config()
        meta = config.get("metadata", {}) or {}
        settings = self.get_theme_settings()
        return {
            "version": config.get("version", "1.0"),
            "metadata": {
                "name": getattr(self, "name", "") or meta.get("name", ""),
                "slug": getattr(self, "slug", ""),
                "version": getattr(self, "version", ""),
                "description": getattr(self, "description", "") or meta.get("description", ""),
                "author": getattr(self, "author", "") or meta.get("author", ""),
            },
            "settings": settings,
            "settings_schema": self.get_settings_schema(),
            "layout": settings.get("layout", config.get("layout", {})),
            "components": settings.get("components", config.get("components", {})),
            "componentSlots": self.get_component_slots(),
            "supports": config.get("supports", []),
            "screenshot": self.get_screenshot_path(),
            "css_url": "/api/v2/themes/active/css",
            "config_url": "/api/v2/themes/active/config",
        }

    # ─── 生命周期 ──────────────────────────

    def activate(self):
        """激活主题 - 注册 theme.activated 事件"""
        super().activate()
        # 广播主题激活事件（async emit 在 sync 上下文中通过 create_task 调度）
        import asyncio
        from shared.services.plugins.event_bus import event_bus
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.emit("theme.activated", {
                "slug": self.slug,
                "name": self.name,
                "settings": self.get_theme_settings(),
            }))
        except RuntimeError:
            pass  # 无运行中的事件循环时忽略

    def deactivate(self):
        """停用主题 - 注册 theme.deactivated 事件"""
        super().deactivate()
        import asyncio
        from shared.services.plugins.event_bus import event_bus
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.emit("theme.deactivated", {
                "slug": self.slug,
                "name": self.name,
            }))
        except RuntimeError:
            pass

    # ─── 插件信息增强 ──────────────────────────

    def get_info(self) -> dict:
        """获取主题插件信息（在 BasePlugin 基础上补充主题专属字段）"""
        info = super().get_info()
        config = self.get_theme_config()
        info.update({
            "screenshot": self.get_screenshot_path(),
            "supports": config.get("supports", []),
            "settings_schema": self.get_settings_schema(),
            "theme_config": config.get("settings", {}),
        })
        return info
