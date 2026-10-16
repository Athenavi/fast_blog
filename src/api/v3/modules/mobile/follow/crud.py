"""follow 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.user.user_follow import UserFollow
from src.api.v3.core.base_crud import CRUDBase


class UserFollowCRUD(CRUDBase[UserFollow, dict, dict]):
    model = UserFollow
    #: 关注列表按关注时间倒序（新的在前）
    default_order_by = "created_at"


user_follow_crud = UserFollowCRUD()
