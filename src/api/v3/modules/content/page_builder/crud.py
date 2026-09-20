"""page_builder 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.page import PageBuilder
from src.api.v3.core.base_crud import CRUDBase


class PageBuilderCRUD(CRUDBase[PageBuilder, dict, dict]):
    model = PageBuilder
    keyword_fields = ("title", "slug")
    default_order_by = "updated_at"


page_builder_crud = PageBuilderCRUD()
