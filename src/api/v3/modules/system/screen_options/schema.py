"""screen_options 模块的请求模型

只放「无法用原生类型表达」的请求体。``PUT /{page}`` 刻意收**原始 dict**
（见 controller），避免 pydantic 模型把未知选项键静默丢弃。
"""

from typing import Any

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class OptionValueUpdate(SchemaBase):
    """``PATCH /{page}/{key}``：单项的新值（任意 JSON 可序列化的值，可为 ``null``）"""

    value: Any = Field(..., description="新的选项值（任意 JSON 可序列化的值）")
