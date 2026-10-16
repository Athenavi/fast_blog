"""redirect 模块的请求模型"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class RedirectCreate(SchemaBase):
    from_path: str = Field(min_length=1, max_length=500, description="源路径（可传完整 URL，服务端会归一）")
    to_path: str = Field(min_length=1, max_length=500, description="目标路径或绝对 URL")
    status_code: int = Field(default=301, description="301 / 302 / 307 / 308")
    is_active: bool = True
    notes: Optional[str] = Field(default=None, max_length=1000)


class RedirectUpdate(SchemaBase):
    from_path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    to_path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    status_code: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class RedirectBatchRequest(SchemaBase):
    """批量导入（对应 v2 的 ``bulk_import``）"""

    items: list[RedirectCreate] = Field(min_length=1, max_length=1000)
    overwrite: bool = Field(default=True, description="false 时已存在的源路径按跳过计数")


class RedirectQuery(SchemaBase):
    path: str = Field(min_length=1, max_length=500, description="站点内路径或完整 URL")
