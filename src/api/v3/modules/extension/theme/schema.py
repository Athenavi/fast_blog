"""theme 模块的请求 / 响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ThemeInfoOut(SchemaBase):
    """当前主题信息（字段随 ``ThemePlugin.get_info()`` 变化，保持宽松）"""

    slug: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    screenshot: Optional[str] = None
    supports: Optional[Any] = None
    is_active: Optional[bool] = None
    model_config = {"extra": "allow"}


class ThemeConfigOut(SchemaBase):
    slug: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    component_slots: Dict[str, Any] = Field(default_factory=dict)
    settings_schema: Optional[Any] = None


class ThemeConfigUpdate(SchemaBase):
    settings: Dict[str, Any] = Field(default_factory=dict, description="主题设置项")
    component_slots: Optional[Dict[str, Any]] = Field(
        default=None, description="组件槽位映射（当前主题实现不支持时会被忽略并记录告警）"
    )


class ThemeCssOut(SchemaBase):
    slug: Optional[str] = None
    css: str = ""
    length: int = 0


class ThemeContractOut(SchemaBase):
    """主题契约（供前端做主题适配）"""

    contract: Dict[str, Any] = Field(default_factory=dict)


class ThemeSchemaOut(SchemaBase):
    slug: Optional[str] = None
    settings_schema: Dict[str, Any] = Field(default_factory=dict)
    slots: List[str] = Field(default_factory=list)
