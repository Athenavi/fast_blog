"""user 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.user import User
from src.api.v3.core.base_crud import CRUDBase
from src.api.v3.modules.system.user.schema import UserCreate, UserUpdate


class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    """用户 CRUD

    ``User`` 没有软删除字段（``shared/models/user/user.py``），因此 ``remove`` 为物理删除；
    停用请走 ``activate/deactivate``（见 service）。
    """

    model = User
    keyword_fields = ("username", "email")
    default_order_by = "id"


user_crud = UserCRUD()
