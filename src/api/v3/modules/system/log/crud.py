"""log 模块的数据访问层（唯一 DB 访问点）

审计日志的查询走 ``audit_log_service``（它已封装 ``audit_logs`` 的过滤与分页），
这里只额外提供 CRUDBase 供后续需要精细过滤时使用。
"""

from shared.models.system import AuditLog
from src.api.v3.core.base_crud import CRUDBase


class AuditLogCRUD(CRUDBase[AuditLog, dict, dict]):
    model = AuditLog
    keyword_fields = ("action", "description", "user_name")
    default_order_by = "id"


audit_log_crud = AuditLogCRUD()
