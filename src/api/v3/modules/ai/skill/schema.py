"""skill 模块的请求模型"""

from typing import Any, Dict, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class SkillRunRequest(SchemaBase):
    """执行技能：参数由技能自己声明（见 ``GET /ai/skill`` 的 params）"""

    params: Dict[str, Any] = Field(default_factory=dict, description="技能参数（键见技能详情）")
    config_id: Optional[int] = Field(
        default=None, description="需要调用 LLM 的技能用它指定 AI 配置；留空则取第一条"
    )
