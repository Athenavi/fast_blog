"""
Enterprise Plugin
企业管理：许可证、支持工单、部署脚本、监控告警
"""

from shared.services.plugins.plugin_manager.core import BasePlugin


class EnterprisePlugin(BasePlugin):
    """企业功能插件"""

    def __init__(self):
        super().__init__(
            plugin_id=2001,
            name="Enterprise",
            slug="enterprise",
            version="1.0.0",
            description="企业管理功能：许可证、支持工单、部署脚本、监控告警",
            author="FastBlog Team",
        )

    def subscribers(self) -> list:
        return []


plugin_instance = EnterprisePlugin()
