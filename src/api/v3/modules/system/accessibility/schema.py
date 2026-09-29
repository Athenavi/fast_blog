"""accessibility 模块的请求模型"""

from typing import Any, Dict, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AccessibilityConfigUpdate(SchemaBase):
    """无障碍配置（全部可选，只更新传入的项）"""

    keyboard_navigation: Optional[bool] = None
    screen_reader_support: Optional[bool] = None
    high_contrast_mode: Optional[bool] = None
    font_size: Optional[str] = Field(
        default=None, max_length=20, description="small / medium / large / x-large"
    )
    reduce_motion: Optional[bool] = None
    focus_visible: Optional[bool] = None
    skip_links: Optional[bool] = None


class AriaRequest(SchemaBase):
    """生成某个元素类型的 ARIA 属性建议"""

    element_type: str = Field(min_length=1, max_length=50)
    context: Dict[str, Any] = Field(default_factory=dict, description="可覆盖默认标签，如 {label: '主导航'}")


class AccessibilityValidateRequest(SchemaBase):
    """校验一段 HTML 的无障碍问题"""

    html: str = Field(min_length=1, max_length=500_000)
