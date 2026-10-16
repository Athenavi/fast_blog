"""enterprise 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.enterprise import DataRetentionPolicy, EnterpriseLicense
from src.api.v3.core.base_crud import CRUDBase


class EnterpriseLicenseCRUD(CRUDBase[EnterpriseLicense, dict, dict]):
    model = EnterpriseLicense
    keyword_fields = ("license_key", "license_type", "company_name", "contact_email")
    default_order_by = "id"


class DataRetentionPolicyCRUD(CRUDBase[DataRetentionPolicy, dict, dict]):
    model = DataRetentionPolicy
    keyword_fields = ("data_category", "action")
    default_order_by = "id"


enterprise_license_crud = EnterpriseLicenseCRUD()
data_retention_policy_crud = DataRetentionPolicyCRUD()
