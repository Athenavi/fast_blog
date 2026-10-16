"""V3 分页 / 查询基类

结构对齐 FastApiAdmin `app/core/base_schema.py`，只保留 fast_blog 实际需要的部分：
  1. ``SchemaBase``：所有响应 schema 的基类，统一 ``from_attributes`` 行为
  2. ``TimeRangeQuery``：时间范围筛选的公共字段
  3. ``PageResult``：分页结果结构（与 ``common/response.py`` 的 pagination 对应）
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class SchemaBase(BaseModel):
    """V3 schema 基类

    直接由 SQLAlchemy 模型构造（``Model.model_validate(obj)``）时依赖 ``from_attributes``。
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimeRangeQuery(BaseModel):
    """时间范围筛选（作为依赖时字段自动成为 query 参数）"""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PageResult(BaseModel, Generic[T]):
    """分页结果结构（内部使用；HTTP 响应统一走 ``common/response.success_page``）"""

    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 0
