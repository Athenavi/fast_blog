"""
Migration Plugin
内容迁移工具：从 WordPress、Halo 等平台迁移内容到 FastBlog
"""

from shared.services.plugins.plugin_manager.core import BasePlugin


class MigrationPlugin(BasePlugin):
    """内容迁移插件"""

    def __init__(self):
        super().__init__(
            plugin_id=2002,
            name="Migration",
            slug="migration",
            version="1.0.0",
            description="内容迁移工具：从 WordPress、Halo 等平台迁移内容到 FastBlog",
            author="FastBlog Team",
        )

    def subscribers(self) -> list:
        return []


plugin_instance = MigrationPlugin()
