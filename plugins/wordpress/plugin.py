"""WordPress Style Theme

经典博客风主题：顶部导航 + 主栏/侧栏两列、文章列表带摘要、文章页带标签与相关文章。

## 页面来自哪里

本主题**不提供编译期 Vue 组件** —— 页面结构全部声明在 `theme.json` 的 `templates` 里，
由前台内置的区块渲染器解释执行（L1 声明式区块）。

这样做的意义：**改 `theme.json` 刷新即生效，不需要重新构建** —— 主题才是真正可热插拔的。
（对照：L2 主题会在 `frontend/site/` 放 `.vue`，表现力更强但要自己构建。）
"""

from shared.logging import default_logger as logger
from shared.services.plugins.plugin_manager.theme_plugin import ThemePlugin


class WordPressTheme(ThemePlugin):
    """WordPress Style 主题"""

    def __init__(self):
        super().__init__(
            plugin_id=1001,
            name="WordPress Style",
            slug="wordpress",
            version="1.0.0",
            description="经典博客风：顶部导航 + 主栏/侧栏两列、文章列表带摘要、文章页带标签与相关文章",
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
        logger.info(f"[WordPressTheme] 经典博客主题已激活: {payload}")


# 模块级实例（插件系统通过此变量发现）
plugin_instance = WordPressTheme()
