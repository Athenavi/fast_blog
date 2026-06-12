"""
Content Approval Plugin
内容审批工作流：待审批、我的申请、统计历史
"""

from shared.services.plugins.plugin_manager.core import BasePlugin


class ApprovalPlugin(BasePlugin):
    """内容审批插件"""

    def __init__(self):
        super().__init__(
            plugin_id=2003,
            name="Content Approval",
            slug="approval",
            version="1.0.0",
            description="内容审批工作流：待审批、我的申请、统计历史",
            author="FastBlog Team",
        )

    def subscribers(self) -> list:
        return []


plugin_instance = ApprovalPlugin()
