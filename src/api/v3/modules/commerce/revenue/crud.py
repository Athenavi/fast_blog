"""revenue 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.revenue import (
    PayoutRequest,
    RevenueRecord,
    RevenueSharingConfig,
    UserRevenueStats,
)
from src.api.v3.core.base_crud import CRUDBase


class RevenueRecordCRUD(CRUDBase[RevenueRecord, dict, dict]):
    model = RevenueRecord
    keyword_fields = ("description", "reference_type")
    #: 收益流水以时间为序（新在前）
    default_order_by = "created_at"


class PayoutRequestCRUD(CRUDBase[PayoutRequest, dict, dict]):
    model = PayoutRequest
    keyword_fields = ("payment_account", "account_name", "admin_notes")
    default_order_by = "created_at"


class RevenueSharingConfigCRUD(CRUDBase[RevenueSharingConfig, dict, dict]):
    model = RevenueSharingConfig
    keyword_fields = ("revenue_type", "description")
    default_order_by = "id"


class UserRevenueStatsCRUD(CRUDBase[UserRevenueStats, dict, dict]):
    model = UserRevenueStats
    default_order_by = "user_id"


revenue_record_crud = RevenueRecordCRUD()
payout_request_crud = PayoutRequestCRUD()
revenue_sharing_config_crud = RevenueSharingConfigCRUD()
user_revenue_stats_crud = UserRevenueStatsCRUD()
