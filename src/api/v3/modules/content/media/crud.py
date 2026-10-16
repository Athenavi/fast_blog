"""media 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.media.media import Media
from shared.models.media.media_folder import MediaFolder
from src.api.v3.core.base_crud import CRUDBase


class MediaCRUD(CRUDBase[Media, dict, dict]):
    model = Media
    keyword_fields = ("filename", "original_filename", "description", "alt_text")
    default_order_by = "id"


class MediaFolderCRUD(CRUDBase[MediaFolder, dict, dict]):
    model = MediaFolder
    keyword_fields = ("name", "description")
    default_order_by = "sort_order"


media_crud = MediaCRUD()
media_folder_crud = MediaFolderCRUD()
