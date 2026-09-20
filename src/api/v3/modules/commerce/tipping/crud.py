"""tipping 模块的数据访问层（唯一 DB 访问点）

两张表：``tips``（打赏）/ ``tip_withdrawals``（提现）。
"""

from shared.models.tipping import Tip, TipWithdrawal
from src.api.v3.core.base_crud import CRUDBase


class TipCRUD(CRUDBase[Tip, dict, dict]):
    model = Tip
    keyword_fields = ("order_no", "message")
    default_order_by = "created_at"


class TipWithdrawalCRUD(CRUDBase[TipWithdrawal, dict, dict]):
    model = TipWithdrawal
    default_order_by = "created_at"


tip_crud = TipCRUD()
tip_withdrawal_crud = TipWithdrawalCRUD()
