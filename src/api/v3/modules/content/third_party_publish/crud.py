"""third_party_publish 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.third_party_publish import PublishChannel, PublishLog, PublishTask
from src.api.v3.core.base_crud import CRUDBase


class PublishChannelCRUD(CRUDBase[PublishChannel, dict, dict]):
    model = PublishChannel
    keyword_fields = ("name", "platform", "endpoint")
    default_order_by = "id"


class PublishTaskCRUD(CRUDBase[PublishTask, dict, dict]):
    model = PublishTask
    default_order_by = "id"


class PublishLogCRUD(CRUDBase[PublishLog, dict, dict]):
    model = PublishLog
    default_order_by = "id"


publish_channel_crud = PublishChannelCRUD()
publish_task_crud = PublishTaskCRUD()
publish_log_crud = PublishLogCRUD()
