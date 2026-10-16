"""menu 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.menu.menu_items import MenuItems
from shared.models.menu.menus import Menus
from src.api.v3.core.base_crud import CRUDBase


class MenuCRUD(CRUDBase[Menus, dict, dict]):
    model = Menus
    keyword_fields = ("name", "slug", "description")
    default_order_by = "id"


class MenuItemCRUD(CRUDBase[MenuItems, dict, dict]):
    model = MenuItems
    keyword_fields = ("title", "url")
    default_order_by = "order_index"


menu_crud = MenuCRUD()
menu_item_crud = MenuItemCRUD()
