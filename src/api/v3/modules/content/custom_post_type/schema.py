"""custom_post_type 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase
from src.api.v3.modules.content.custom_post_type.field_spec import (
    dump_fields,
    validate_field_definitions,
)


class CustomPostTypeCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9_-]+$")
    description: Optional[str] = Field(default=None, max_length=255)
    supports: Optional[str] = Field(default=None, max_length=255,
                                    description="支持的功能（逗号分隔：title,editor,thumbnail…）")
    has_archive: bool = False
    menu_icon: Optional[str] = Field(default=None, max_length=100)
    menu_position: int = Field(default=0, ge=0)
    is_active: bool = True
    fields: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="字段定义（JSON 数组文本）：key/type/label/required/options…；非法定义直接 400",
    )

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value):
        """**入参即校验**并把定义规范化后回写，避免非法定义落库后前端渲染出错。"""
        return dump_fields(validate_field_definitions(value))


class CustomPostTypeUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    supports: Optional[str] = Field(default=None, max_length=255)
    has_archive: Optional[bool] = None
    menu_icon: Optional[str] = Field(default=None, max_length=100)
    menu_position: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    fields: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value):
        return dump_fields(validate_field_definitions(value))


class CustomPostTypeOut(SchemaBase):
    id: int
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    supports: Optional[str] = None
    has_archive: bool = False
    menu_icon: Optional[str] = None
    menu_position: int = 0
    is_active: bool = True
    fields: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomFieldValuesUpdate(SchemaBase):
    """字段值写入。

    字段结构由类型定义的 ``fields`` 决定，这里只声明外层容器；
    未定义的 key、类型不符、必填缺失都会在 service 层被拒（400）。
    """

    values: Dict[str, Any] = Field(
        default_factory=dict,
        description="字段 key → 值；存在未定义 key 或必填缺失会被拒绝",
    )
