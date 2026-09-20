"""badge 模块的数据访问层（唯一 DB 访问点）

两张表：``badge_definitions``（定义）/ ``user_badges``（已获）。
"""

from shared.models.gamification import BadgeDefinition, UserBadge
from src.api.v3.core.base_crud import CRUDBase


class BadgeDefinitionCRUD(CRUDBase[BadgeDefinition, dict, dict]):
    model = BadgeDefinition
    keyword_fields = ("badge_key", "name", "description")
    default_order_by = "sort_order"


class UserBadgeCRUD(CRUDBase[UserBadge, dict, dict]):
    model = UserBadge
    #: 已获勋章以授予时间为序（新在前）
    default_order_by = "awarded_at"


badge_definition_crud = BadgeDefinitionCRUD()
user_badge_crud = UserBadgeCRUD()
