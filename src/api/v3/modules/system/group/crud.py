"""group 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.rbac.permission_group import PermissionGroup
from shared.models.rbac.role_group import RoleGroup
from shared.models.rbac.user_group_member import UserGroupMember
from src.api.v3.core.base_crud import CRUDBase


class PermissionGroupCRUD(CRUDBase[PermissionGroup, dict, dict]):
    model = PermissionGroup
    keyword_fields = ("name", "code", "description")
    default_order_by = "sort_order"


class UserGroupMemberCRUD(CRUDBase[UserGroupMember, dict, dict]):
    model = UserGroupMember
    default_order_by = "id"


class RoleGroupCRUD(CRUDBase[RoleGroup, dict, dict]):
    model = RoleGroup
    default_order_by = "id"


permission_group_crud = PermissionGroupCRUD()
user_group_member_crud = UserGroupMemberCRUD()
role_group_crud = RoleGroupCRUD()
