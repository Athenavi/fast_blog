"""ad 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.ad import Ad, AdClick, AdImpression, AdPlacement
from src.api.v3.core.base_crud import CRUDBase


class AdCRUD(CRUDBase[Ad, dict, dict]):
    model = Ad
    keyword_fields = ("title", "alt_text")
    default_order_by = "id"


class AdPlacementCRUD(CRUDBase[AdPlacement, dict, dict]):
    model = AdPlacement
    keyword_fields = ("name", "code", "description")
    default_order_by = "id"


class AdClickCRUD(CRUDBase[AdClick, dict, dict]):
    model = AdClick
    default_order_by = "id"


class AdImpressionCRUD(CRUDBase[AdImpression, dict, dict]):
    model = AdImpression
    default_order_by = "id"


ad_crud = AdCRUD()
ad_placement_crud = AdPlacementCRUD()
ad_click_crud = AdClickCRUD()
ad_impression_crud = AdImpressionCRUD()
