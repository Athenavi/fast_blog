"""setting 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.system import SystemSettings
from src.api.v3.core.base_crud import CRUDBase


class SettingCRUD(CRUDBase[SystemSettings, dict, dict]):
    model = SystemSettings
    keyword_fields = ("setting_key", "description")
    default_order_by = "id"


setting_crud = SettingCRUD()
