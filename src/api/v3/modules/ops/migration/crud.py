"""migration 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.migration import MigrationLog, MigrationTask
from src.api.v3.core.base_crud import CRUDBase


class MigrationTaskCRUD(CRUDBase[MigrationTask, dict, dict]):
    model = MigrationTask
    keyword_fields = ("task_name", "source_platform")
    default_order_by = "id"


class MigrationLogCRUD(CRUDBase[MigrationLog, dict, dict]):
    model = MigrationLog
    default_order_by = "id"


migration_task_crud = MigrationTaskCRUD()
migration_log_crud = MigrationLogCRUD()
