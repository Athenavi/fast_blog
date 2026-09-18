"""plugin 模块的请求 / 响应模型"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class PluginOut(SchemaBase):
    """插件信息（字段随 ``BasePlugin.get_info()`` 变化，保持宽松）"""

    slug: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    is_installed: Optional[bool] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    settings_schema: Optional[Any] = None
    model_config = {"extra": "allow"}


class PluginSettingsUpdate(SchemaBase):
    settings: Dict[str, Any] = Field(default_factory=dict, description="要写入的配置项")


class PluginSettingsOut(SchemaBase):
    slug: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    settings_schema: Optional[Any] = None


class PluginScanOut(SchemaBase):
    new_plugins: List[str] = Field(default_factory=list)
    count: int = 0


class PluginActionOut(SchemaBase):
    slug: str
    action: str
    success: bool = True
    detail: Optional[str] = None
