"""V3 统一请求模型

结构对齐 FastApiAdmin `app/common/request.py`：把分页 / 排序 / 关键词查询抽成可复用的
依赖模型，避免每个 controller 重复声明 ``page: int = Query(1, ge=1)``。

用法::

    from src.api.v3.core.deps import PageDep

    @router.get("/list")
    async def list_users(page: PageDep, db: DBSession):
        ...
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PageQuery(BaseModel):
    """分页查询依赖（作为 FastAPI 依赖时，字段自动成为 query 参数）"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页条数")
    keyword: Optional[str] = Field(default=None, description="模糊搜索关键词")
    order_by: Optional[str] = Field(default=None, description="排序字段名（须为模型列名）")
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class SortQuery(BaseModel):
    """仅排序查询依赖"""

    order_by: Optional[str] = Field(default=None, description="排序字段名（须为模型列名）")
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")


class IdsRequest(BaseModel):
    """批量操作请求体"""

    ids: list[int] = Field(default_factory=list, description="主键列表")

    class Config:
        json_schema_extra = {"example": {"ids": [1, 2, 3]}}
