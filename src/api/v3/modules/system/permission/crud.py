"""permission 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.rbac.capability import Capability
from src.api.v3.core.base_crud import CRUDBase


class CapabilityCRUD(CRUDBase[Capability, dict, dict]):
    model = Capability
    keyword_fields = ("code", "name", "description")
    default_order_by = "code"


capability_crud = CapabilityCRUD()
