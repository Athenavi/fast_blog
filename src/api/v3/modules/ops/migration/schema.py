"""migration 模块的请求 / 响应模型"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


class MigrationTaskCreate(SchemaBase):
    task_name: str = Field(min_length=1, max_length=200)
    source_platform: str = Field(max_length=50, description="来源平台（wordpress/jekyll/hexo…）")
    config: Optional[dict] = Field(default=None, description="任务配置（JSON，由导入器解释）")
    total_items: int = Field(default=0, ge=0)


class MigrationTaskUpdate(SchemaBase):
    task_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    config: Optional[dict] = None
    total_items: Optional[int] = Field(default=None, ge=0)


class MigrationTaskOut(SchemaBase):
    id: int
    task_name: Optional[str] = None
    source_platform: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None
    progress: int = 0
    total_items: int = 0
    migrated_items: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("config", mode="before")
    @classmethod
    def _parse_config(cls, v: object) -> object:
        """DB 列是 JSON 字符串，序列化时转字典"""
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"raw": v}
        return v


class MigrationLogOut(SchemaBase):
    id: int
    task_id: int
    log_level: Optional[str] = None
    message: Optional[str] = None
    item_type: Optional[str] = None
    item_id: Optional[int] = None
    created_at: Optional[datetime] = None
