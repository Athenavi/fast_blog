"""page_builder 模块的请求 / 响应模型

``blocks_data`` 是拖拽布局的块数组：入参为 ``list[dict]``，落库 ``json.dumps`` 成文本；
出参（``PageBuilderOut``）由 ``field_validator(mode="before")`` 解析回数组，
样板见 ``marketing/vip/schema.py`` 的 ``features`` validator。
"""

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase

#: 拖拽布局块数组（块对象结构由前端定义，后端只透传）
PageBlocks = list[dict[str, Any]]


class PageBuilderCreate(SchemaBase):
    title: Optional[str] = Field(default=None, max_length=255)
    slug: str = Field(min_length=1, max_length=255, description="页面路径标识，创建后锁定")
    blocks_data: PageBlocks = Field(default_factory=list, description="拖拽块布局数据（块对象数组）")
    template_name: Optional[str] = Field(default=None, max_length=100)
    is_published: bool = False


class PageBuilderUpdate(SchemaBase):
    """更新模型：无 ``slug`` 字段 —— slug 创建后锁定，不允许改"""

    title: Optional[str] = Field(default=None, max_length=255)
    blocks_data: Optional[PageBlocks] = None
    template_name: Optional[str] = Field(default=None, max_length=100)
    is_published: Optional[bool] = None


class PageBuilderPublishRequest(SchemaBase):
    is_published: bool = Field(default=True, description="true=发布，false=撤回")


class PageBuilderOut(SchemaBase):
    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    blocks_data: PageBlocks = Field(default_factory=list)
    template_name: Optional[str] = None
    is_published: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("blocks_data", mode="before")
    @classmethod
    def _parse_blocks(cls, v: object) -> object:
        """DB 列是 JSON 字符串，序列化时解析回块数组；异常值兜底为 []"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                return []
        if isinstance(v, dict):
            return [v]
        return v if isinstance(v, list) else []
