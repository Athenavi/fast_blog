"""mobile/vip 的数据访问层（唯一 DB 访问点：VIP 支付订单）

订阅本身的读写走共享服务 ``shared.services.core.membership.MembershipService``，
这里只负责本模块新增的 ``vip_payment_orders``。
"""

from shared.models.vip import VipPaymentOrder
from src.api.v3.core.base_crud import CRUDBase


class VipPaymentOrderCRUD(CRUDBase[VipPaymentOrder, dict, dict]):
    model = VipPaymentOrder
    keyword_fields = ("order_no", "transaction_id")
    default_order_by = "created_at"


vip_payment_order_crud = VipPaymentOrderCRUD()
