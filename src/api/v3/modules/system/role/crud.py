"""role 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.rbac.role import Role
from src.api.v3.core.base_crud import CRUDBase


class RoleCRUD(CRUDBase[Role, dict, dict]):
    model = Role
    keyword_fields = ("name", "slug", "description")
    default_order_by = "id"


role_crud = RoleCRUD()
