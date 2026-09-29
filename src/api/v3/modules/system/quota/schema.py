"""quota 模块的请求模型

只放「无法用原生类型表达」的请求体。``PUT /{site_id}`` 刻意收**原始 dict**
（见 controller），避免 pydantic 模型把未知配额键静默丢弃。
"""

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class QuotaCheckRequest(SchemaBase):
    """``POST /{site_id}/check``：校验追加 ``requested_amount`` 后是否仍超配额"""

    resource_type: str = Field(
        ..., min_length=1, max_length=50, description="articles / media / users / storage_mb"
    )
    requested_amount: int = Field(default=1, ge=0, description="本次请求追加的数量（默认 1）")
