"""feed 模块的请求模型

关注流只有一个只读端点，请求参数就是分页（``page`` / ``page_size``）。
``page_size`` 上限 50（比通用列表的 100 小：关注流首屏更小，避免一次拉太多）。

本模型字段与 controller 的 Query 参数一一对应，作为对外契约 / 文档对齐之用。
"""

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class FeedQuery(SchemaBase):
    """关注流分页查询"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=50, description="每页条数，上限 50")
