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
from pathlib import Path
from typing import Any, Optional

from shared.services.plugins.plugin_manager.core import BasePlugin


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
            print(f"[ThemePlugin] Failed to save settings for {self.name}: {e}")
            return False

    def get_settings_schema(self) -> dict:
        """
        获取设置架构（用于前端动态渲染配置表单）
        来自 metadata.json 中的 settings_schema
        """
        if self.metadata:
            return self.metadata.get("settings_schema", {})
        return {}

    # ─── 生命周期 ──────────────────────────

    def activate(self):
        """激活主题 - 注册 theme.activated 事件"""
        super().activate()
        # 广播主题激活事件，供前端或其它插件监听
        from shared.services.plugins.event_bus import event_bus
        event_bus.emit("theme.activated", {
            "slug": self.slug,
            "name": self.name,
            "settings": self.get_theme_settings(),
        })

    def deactivate(self):
        """停用主题 - 注册 theme.deactivated 事件"""
        super().deactivate()
        from shared.services.plugins.event_bus import event_bus
        event_bus.emit("theme.deactivated", {
            "slug": self.slug,
            "name": self.name,
        })

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
