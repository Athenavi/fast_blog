"""integration 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.integration import LDAPConfig, SSOProvider
from src.api.v3.core.base_crud import CRUDBase


class SSOProviderCRUD(CRUDBase[SSOProvider, dict, dict]):
    model = SSOProvider
    keyword_fields = ("name", "provider_type")
    default_order_by = "id"


class LDAPConfigCRUD(CRUDBase[LDAPConfig, dict, dict]):
    model = LDAPConfig
    keyword_fields = ("server_url", "bind_dn")
    default_order_by = "id"


sso_provider_crud = SSOProviderCRUD()
ldap_config_crud = LDAPConfigCRUD()
