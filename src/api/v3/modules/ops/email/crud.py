"""email 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.integration import EmailServiceConfig
from shared.models.notification import EmailSubscription
from src.api.v3.core.base_crud import CRUDBase


class EmailConfigCRUD(CRUDBase[EmailServiceConfig, dict, dict]):
    model = EmailServiceConfig
    default_order_by = "id"


class EmailSubscriptionCRUD(CRUDBase[EmailSubscription, dict, dict]):
    model = EmailSubscription
    default_order_by = "id"


email_config_crud = EmailConfigCRUD()
email_subscription_crud = EmailSubscriptionCRUD()
