"""form 模块的请求 / 响应模型"""

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


class FormCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9_-]+$")
    description: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|published|closed)$")
    submit_message: Optional[str] = Field(default=None, max_length=500)
    email_notification: bool = False
    notification_email: Optional[str] = Field(default=None, max_length=200)
    store_submissions: bool = True


class FormUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|published|closed)$")
    submit_message: Optional[str] = Field(default=None, max_length=500)
    email_notification: Optional[bool] = None
    notification_email: Optional[str] = Field(default=None, max_length=200)
    store_submissions: Optional[bool] = None


class FormOut(SchemaBase):
    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    submit_message: Optional[str] = None
    email_notification: bool = False
    notification_email: Optional[str] = None
    store_submissions: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FormFieldCreate(SchemaBase):
    label: str = Field(min_length=1, max_length=200)
    field_type: str = Field(
        default="text",
        pattern="^(text|textarea|email|number|select|checkbox|radio|date)$",
    )
    placeholder: Optional[str] = Field(default=None, max_length=200)
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: bool = False
    options: Optional[str] = Field(default=None, max_length=500, description="select/checkbox/radio 的选项，逗号分隔")
    validation_rules: Optional[str] = Field(default=None, max_length=200)
    default_value: Optional[str] = Field(default=None, max_length=200)
    order_index: int = Field(default=0, ge=0)
    is_active: bool = True


class FormFieldUpdate(SchemaBase):
    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    field_type: Optional[str] = Field(
        default=None, pattern="^(text|textarea|email|number|select|checkbox|radio|date)$"
    )
    placeholder: Optional[str] = Field(default=None, max_length=200)
    help_text: Optional[str] = Field(default=None, max_length=500)
    required: Optional[bool] = None
    options: Optional[str] = Field(default=None, max_length=500)
    validation_rules: Optional[str] = Field(default=None, max_length=200)
    default_value: Optional[str] = Field(default=None, max_length=200)
    order_index: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class FormFieldOut(SchemaBase):
    id: int
    form_id: int
    label: Optional[str] = None
    field_type: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    required: bool = False
    options: Optional[str] = None
    validation_rules: Optional[str] = None
    default_value: Optional[str] = None
    order_index: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FormSubmissionOut(SchemaBase):
    id: int
    form_id: int
    data: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    user_id: Optional[int] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("data", mode="before")
    @classmethod
    def _parse_data(cls, v: object) -> object:
        """DB 列是 JSON 字符串，序列化时转字典"""
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"raw": v}
        return v


class FormPublicSubmitRequest(SchemaBase):
    """前台匿名提交：data 为 {字段名: 值}；必填校验按表单字段定义在服务层执行。

    匿名接口的入参必须**有界**：整包直接 `json.dumps` 落库，不设上限时一个请求
    就能写进几十 MB（nginx 允许 60M 请求体）。
    """

    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def _bound_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 50:
            raise ValueError("字段过多（最多 50 个）")
        total = 0
        for key, item in value.items():
            if len(str(key)) > 100:
                raise ValueError("字段名过长")
            text = json.dumps(item, ensure_ascii=False) if not isinstance(item, str) else item
            if len(text) > 5000:
                raise ValueError(f"字段 {key} 的值过长（最多 5000 字符）")
            total += len(text)
        if total > 20000:
            raise ValueError("提交内容过大（最多 20000 字符）")
        return value
