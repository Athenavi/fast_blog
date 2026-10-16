"""site 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.multisite import Site
from src.api.v3.core.base_crud import CRUDBase


class SiteCRUD(CRUDBase[Site, dict, dict]):
    model = Site
    keyword_fields = ("name", "slug", "domain", "description")
    default_order_by = "id"


site_crud = SiteCRUD()
