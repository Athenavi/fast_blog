"""system/accessibility：无障碍（WCAG 2.1）配置 / 生成 / 校验

配置落 ``system_settings``（键 ``accessibility.config``）；样式、跳过链接、ARIA 为纯生成；
HTML 校验按元素解析。
"""

from src.api.v3.modules.system.accessibility.service import accessibility_service

__all__ = ["accessibility_service"]
