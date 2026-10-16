"""ai.workflow 模块的请求 / 响应模型（input/output 为 JSON 字符串列）"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

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


class WorkflowExecute(SchemaBase):
    """发起一次**真实** AI 任务（会调用配置里的模型）"""

    config_id: int = Field(description="使用哪个 AI 配置（凭据会被解密后用于调用）")
    task_type: str = Field(default="writing_assist", max_length=50, description="见 GET /task-types")
    input: str = Field(min_length=1, description="输入正文；task_type=custom 时就是提示词本身")
    user_id: Optional[int] = Field(default=None, description="归属用户；缺省记为配置的归属用户")
    target_lang: Optional[str] = Field(default=None, max_length=50, description="translate 任务的目标语言")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=128000, description="缺省用配置里的值")
