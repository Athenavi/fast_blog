"""admin_menu 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.rbac.admin_menu import AdminMenu
from shared.models.rbac.role_admin_menu import RoleAdminMenu
from src.api.v3.core.base_crud import CRUDBase


class AdminMenuCRUD(CRUDBase[AdminMenu, dict, dict]):
    model = AdminMenu
    keyword_fields = ("code", "title", "permission_code")
    default_order_by = "sort_order"


class RoleAdminMenuCRUD(CRUDBase[RoleAdminMenu, dict, dict]):
    model = RoleAdminMenu
    default_order_by = "id"


admin_menu_crud = AdminMenuCRUD()
role_admin_menu_crud = RoleAdminMenuCRUD()
