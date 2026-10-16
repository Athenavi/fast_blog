"""custom_post_type 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.content import CustomPostType
from src.api.v3.core.base_crud import CRUDBase


class CustomPostTypeCRUD(CRUDBase[CustomPostType, dict, dict]):
    model = CustomPostType
    keyword_fields = ("name", "slug", "description")
    default_order_by = "id"


custom_post_type_crud = CustomPostTypeCRUD()
