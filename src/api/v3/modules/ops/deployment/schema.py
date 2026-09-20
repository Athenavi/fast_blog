"""deployment 模块的请求 / 响应模型

``parameters`` 在模型层是 Text（JSON 字符串列），本模块约定：

  - 入参为 ``dict | list | null``（对象 / 数组 / 不传）
  - 落库前由 service 层 ``json.dumps(..., ensure_ascii=False)`` 序列化
  - 出参通过 ``field_validator(mode="before")`` 把 JSON 字符串解析回对象
"""

import json
from datetime import datetime
from typing import Optional, Union

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


class DeploymentScriptCreate(SchemaBase):
    content: str = Field(min_length=1, description="脚本内容")
    name: Optional[str] = Field(default=None, max_length=255)
    script_type: Optional[str] = Field(default=None, max_length=50)
    version: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None)
    parameters: Optional[Union[dict, list]] = Field(default=None, description="参数定义（对象/数组）")
    is_active: bool = True


class DeploymentScriptUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, max_length=255)
    script_type: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = Field(default=None, min_length=1)
    version: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None)
    parameters: Optional[Union[dict, list]] = None
    is_active: Optional[bool] = None


class DeploymentScriptOut(SchemaBase):
    id: int
    name: Optional[str] = None
    script_type: Optional[str] = None
    content: str
    version: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Union[dict, list]] = None
    is_active: bool = True
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("parameters", mode="before")
    @classmethod
    def _parse_parameters(cls, value):
        """落库的 JSON 字符串 → dict/list；无法解析的脏数据回退 None，避免列表接口 500"""
        if value is None or isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except ValueError:
                return None
            return parsed if isinstance(parsed, (dict, list)) else None
        return None


class DeploymentLogOut(SchemaBase):
    id: int
    script_id: Optional[int] = None
    user_id: Optional[int] = None
    status: Optional[str] = None
    output: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
