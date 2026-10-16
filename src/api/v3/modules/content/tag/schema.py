"""tag 模块的请求 / 响应模型"""

from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class TagOut(SchemaBase):
    name: str
    count: int = 0


class TagRenameRequest(SchemaBase):
    old_name: str = Field(min_length=1, max_length=100)
    new_name: str = Field(min_length=1, max_length=100)


class TagDeleteRequest(SchemaBase):
    name: str = Field(min_length=1, max_length=100)


class TagRenameResult(SchemaBase):
    old_name: str
    new_name: str
    affected: int = 0
    merged: bool = Field(default=False, description="目标标签已存在时表示发生了合并")


class TagDeleteResult(SchemaBase):
    name: str
    affected: int = 0


class TagListResult(SchemaBase):
    items: List[TagOut] = Field(default_factory=list)
    total: int = 0
    limit: Optional[int] = None
