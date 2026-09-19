"""ai.config 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.ai import AIConfig
from src.api.v3.core.base_crud import CRUDBase


class AIConfigCRUD(CRUDBase[AIConfig, dict, dict]):
    model = AIConfig
    keyword_fields = ("name", "model", "provider")
    default_order_by = "id"


ai_config_crud = AIConfigCRUD()
