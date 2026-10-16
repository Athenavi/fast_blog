"""block_pattern 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.widget import BlockPattern
from src.api.v3.core.base_crud import CRUDBase


class BlockPatternCRUD(CRUDBase[BlockPattern, dict, dict]):
    model = BlockPattern
    keyword_fields = ("name", "title", "keywords", "category")
    default_order_by = "id"


block_pattern_crud = BlockPatternCRUD()
