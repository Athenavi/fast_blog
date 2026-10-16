"""security 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.security import LoginAttempt, TokenBlacklist
from src.api.v3.core.base_crud import CRUDBase


class LoginAttemptCRUD(CRUDBase[LoginAttempt, dict, dict]):
    model = LoginAttempt
    default_order_by = "id"


class TokenBlacklistCRUD(CRUDBase[TokenBlacklist, dict, dict]):
    model = TokenBlacklist
    default_order_by = "id"


login_attempt_crud = LoginAttemptCRUD()
token_blacklist_crud = TokenBlacklistCRUD()
