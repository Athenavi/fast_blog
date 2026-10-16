"""shortcode 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ShortcodeCreate(SchemaBase):
    code: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9_-]+$",
                      description="短代码标识（如 ad-banner），创建后锁定")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    content: str = Field(min_length=1, description="替换内容（HTML/模板片段）")
    is_active: bool = True


class ShortcodeUpdate(SchemaBase):
    # code 创建后锁定：更新 schema 不含 code 字段（多传会被 Pydantic 忽略）
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    is_active: Optional[bool] = None


class ShortcodeOut(SchemaBase):
    id: int
    code: str
    name: Optional[str] = None
    description: Optional[str] = None
    content: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
