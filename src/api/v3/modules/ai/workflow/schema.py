"""ai.workflow 模块的请求 / 响应模型（input/output 为 JSON 字符串列）"""

import json
from datetime import datetime
from typing import Optional

from pydantic import field_validator

from src.api.v3.core.base_schema import SchemaBase


def _loads_json(value):  # noqa: ANN001, ANN202 - pydantic validator
    if value is None or isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


class AIWorkflowOut(SchemaBase):
    id: int
    user_id: Optional[int] = None
    task_type: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    model_used: Optional[str] = None
    tokens_used: int = 0
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # JSON 字符串列：先解析再校验
    @field_validator("input_data", "output_data", mode="before")
    @classmethod
    def _parse_json_columns(cls, value):  # noqa: ANN001, ANN202
        return _loads_json(value)
