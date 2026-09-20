"""shortcode 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.content import Shortcode
from src.api.v3.core.base_crud import CRUDBase


class ShortcodeCRUD(CRUDBase[Shortcode, dict, dict]):
    model = Shortcode
    keyword_fields = ("code", "name", "description")
    default_order_by = "id"


shortcode_crud = ShortcodeCRUD()
