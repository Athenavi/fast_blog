"""category 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.category.category import Category
from src.api.v3.core.base_crud import CRUDBase


class CategoryCRUD(CRUDBase[Category, dict, dict]):
    model = Category
    keyword_fields = ("name", "slug", "description")
    default_order_by = "sort_order"


category_crud = CategoryCRUD()
