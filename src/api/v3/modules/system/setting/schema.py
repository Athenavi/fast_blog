"""setting 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SettingOut(SchemaBase):
    id: int
    setting_key: str
    setting_value: Optional[str] = None
    parsed_value: Optional[Any] = Field(default=None, description="按 setting_type 解析后的值")
    setting_type: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SettingUpsert(SchemaBase):
    setting_key: str = Field(min_length=1, max_length=100)
    setting_value: Optional[str] = None
    setting_type: str = Field(default="string", description="string / int / float / bool / json")
    description: Optional[str] = None
    is_public: bool = False


class SettingValueUpdate(SchemaBase):
    setting_value: Optional[str] = None
    setting_type: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class SettingBatchUpsert(SchemaBase):
    items: List[SettingUpsert] = Field(default_factory=list, description="批量写入（按 key upsert）")
