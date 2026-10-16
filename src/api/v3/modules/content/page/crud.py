"""page 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.page.pages import Pages
from src.api.v3.core.base_crud import CRUDBase


class PageCRUD(CRUDBase[Pages, dict, dict]):
    model = Pages
    keyword_fields = ("title", "slug", "excerpt")
    default_order_by = "order_index"


page_crud = PageCRUD()
