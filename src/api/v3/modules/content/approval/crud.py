"""approval 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.collaboration import ApprovalRecord, ApprovalStep
from src.api.v3.core.base_crud import CRUDBase


class ApprovalRecordCRUD(CRUDBase[ApprovalRecord, dict, dict]):
    model = ApprovalRecord
    default_order_by = "id"


class ApprovalStepCRUD(CRUDBase[ApprovalStep, dict, dict]):
    model = ApprovalStep
    default_order_by = "id"


approval_record_crud = ApprovalRecordCRUD()
approval_step_crud = ApprovalStepCRUD()
