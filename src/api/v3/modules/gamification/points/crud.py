"""points 模块的数据访问层（唯一 DB 访问点）

三张表：``user_points``（账户）/ ``points_transactions``（流水）/ ``points_rules``（规则）。
"""

from shared.models.gamification import PointsRule, PointsTransaction, UserPoints
from src.api.v3.core.base_crud import CRUDBase


class UserPointsCRUD(CRUDBase[UserPoints, dict, dict]):
    model = UserPoints
    #: 排行榜按余额倒序
    default_order_by = "balance"


class PointsTransactionCRUD(CRUDBase[PointsTransaction, dict, dict]):
    model = PointsTransaction
    keyword_fields = ("action", "description")
    #: 流水以发生时间为序（新在前）
    default_order_by = "created_at"


class PointsRuleCRUD(CRUDBase[PointsRule, dict, dict]):
    model = PointsRule
    keyword_fields = ("action", "description")
    default_order_by = "sort_order"


user_points_crud = UserPointsCRUD()
points_transaction_crud = PointsTransactionCRUD()
points_rule_crud = PointsRuleCRUD()
