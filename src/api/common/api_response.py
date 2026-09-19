"""跨版本共享的基础响应模型

自 ``src/api/v2/_base.py`` 上移（T5-12 v2 下线）：错误处理器（``src/app.py``、
``src/utils/exception_handler.py``）在 v2/v3 之外仍需要这个 legacy 形状
``{success, data, message, error, pagination}``，故放到版本无关的位置。
"""
from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """通用 API 响应模型（legacy 形状，v2 时代统一错误响应沿用）"""

    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    pagination: Optional[dict] = None
