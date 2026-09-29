"""system/help：帮助中心（默认主题 + 自定义持久化 + 相关性搜索 + 字段提示 + 视频）

自定义 / 覆盖条目落 ``system_settings``（键 ``help.topics``）；默认主题为内置常量
（``DEFAULT_TOPICS``，内容照搬 v2）；搜索与字段提示为真实计算，非硬编码。
"""

from src.api.v3.modules.system.help.service import help_service

__all__ = ["help_service"]
