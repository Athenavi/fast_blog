"""social 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.user import OAuthAccount
from src.api.v3.core.base_crud import CRUDBase


class OAuthAccountCRUD(CRUDBase[OAuthAccount, dict, dict]):
    model = OAuthAccount
    default_order_by = "id"


oauth_account_crud = OAuthAccountCRUD()
