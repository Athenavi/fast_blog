"""vip 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.vip import VIPFeature, VIPPlan, VIPSubscription
from src.api.v3.core.base_crud import CRUDBase


class VipPlanCRUD(CRUDBase[VIPPlan, dict, dict]):
    model = VIPPlan
    keyword_fields = ("name", "description")
    default_order_by = "id"


class VipFeatureCRUD(CRUDBase[VIPFeature, dict, dict]):
    model = VIPFeature
    keyword_fields = ("code", "name", "description")
    default_order_by = "id"


class VipSubscriptionCRUD(CRUDBase[VIPSubscription, dict, dict]):
    model = VIPSubscription
    default_order_by = "id"


vip_plan_crud = VipPlanCRUD()
vip_feature_crud = VipFeatureCRUD()
vip_subscription_crud = VipSubscriptionCRUD()
