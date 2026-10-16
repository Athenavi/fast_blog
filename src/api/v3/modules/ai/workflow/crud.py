"""ai.workflow 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.ai.ai_workflow import AIWorkflow  # 包 __init__ 未导出该模型（生成器产物）
from src.api.v3.core.base_crud import CRUDBase


class AIWorkflowCRUD(CRUDBase[AIWorkflow, dict, dict]):
    model = AIWorkflow
    keyword_fields = ("task_type", "model_used")
    default_order_by = "id"


ai_workflow_crud = AIWorkflowCRUD()
