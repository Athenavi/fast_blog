"""system.workflow 模块的请求模型

定义本身结构自由（``nodes`` 等），所以用一个 ``Dict[str, Any]`` 承载而非逐字段建模——
pydantic 会原样保留嵌套 dict，service 里的 ``validate_definition`` 才是权威校验。
"""

from typing import Any, Dict, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class WorkflowDefinitionSave(SchemaBase):
    """注册 / 覆盖一个工作流定义"""

    workflow_id: str = Field(min_length=1, max_length=100, description="工作流标识（唯一）")
    definition: Dict[str, Any] = Field(description="工作流定义：至少含 nodes 列表")


class WorkflowDefinitionValidate(SchemaBase):
    """只校验不保存一个工作流定义"""

    definition: Dict[str, Any] = Field(description="待校验的工作流定义")


class WorkflowInstanceCreate(SchemaBase):
    """创建一个工作流实例"""

    workflow_id: str = Field(min_length=1, max_length=100, description="已注册的工作流标识")
    context: Dict[str, Any] = Field(default_factory=dict, description="实例上下文变量")


class WorkflowApproval(SchemaBase):
    """审批（通过 / 拒绝）时附带的说明"""

    comment: Optional[str] = Field(default=None, max_length=500, description="审批意见")
