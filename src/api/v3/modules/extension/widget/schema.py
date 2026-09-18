"""widget 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.common.json_field import dump_json_field, parse_json_field
from src.api.v3.core.base_schema import SchemaBase

__all__ = [
    "WidgetOut",
    "WidgetCreate",
    "WidgetUpdate",
    "WidgetToggleRequest",
    "WidgetReorderItem",
    "WidgetReorderRequest",
    "WidgetTypeOut",
    "WidgetAreaOut",
    "parse_json_field",
    "dump_json_field",
]


class WidgetOut(SchemaBase):
    id: int
    widget_type: str
    area: str
    title: Optional[str] = None
    config: Optional[Any] = None
    order_index: int = 0
    is_active: bool = True
    conditions: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WidgetCreate(SchemaBase):
    widget_type: str = Field(min_length=1, max_length=50)
    area: str = Field(min_length=1, max_length=50)
    title: Optional[str] = Field(default=None, max_length=255)
    config: Optional[Dict[str, Any]] = None
    order_index: int = 0
    is_active: bool = True
    conditions: Optional[Dict[str, Any]] = None


class WidgetUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, max_length=255)
    config: Optional[Dict[str, Any]] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[Dict[str, Any]] = None


class WidgetToggleRequest(SchemaBase):
    is_active: bool


class WidgetReorderItem(SchemaBase):
    id: int
    order_index: int


class WidgetReorderRequest(SchemaBase):
    items: List[WidgetReorderItem] = Field(default_factory=list)


class WidgetTypeOut(SchemaBase):
    type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    config_schema: Optional[Any] = None
    model_config = {"extra": "allow"}


class WidgetAreaOut(SchemaBase):
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    model_config = {"extra": "allow"}
