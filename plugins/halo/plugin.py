"""Halo Style Theme

现代博客风主题：居中大标题、卡片式文章列表、文章页带元信息与相关文章。

## 页面来自哪里

本主题**不提供编译期 Vue 组件** —— 页面结构声明在 `theme.json` 的 `templates` 里，
由前台内置的区块渲染器解释执行（L1 声明式区块）。

因此**改 `theme.json` 刷新即生效、不需要重新构建** —— 这才是可热插拔的主题。
需要更强表现力时，可在 `frontend/site/` 放 `.vue`（L2，会覆盖 L1），但要自行构建。
"""

from shared.logging import default_logger as logger
from shared.services.plugins.plugin_manager.theme_plugin import ThemePlugin


class HaloTheme(ThemePlugin):
    """Halo Style 主题"""

    def __init__(self):
        super().__init__(
            plugin_id=1002,
            name="Halo Style",
            slug="halo",
            version="1.0.0",
            description="现代博客风：居中大标题、卡片式文章列表、文章页带元信息与相关文章",
            author="FastBlog Team",
            author_url="https://athenavi.github.io",
        )

    def subscribers(self) -> list:
        """注册 EventBus 订阅"""
        return [
            ("theme.activated", self.on_theme_activated),
        ]

    def on_theme_activated(self, payload: dict):
        """主题被激活时的处理"""
        logger.info(f"[HaloTheme] Halo 风格主题已激活: {payload}")


# 模块级实例（插件系统通过此变量发现）
plugin_instance = HaloTheme()
