"""report 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.report import ReportHistory, ScheduledReport
from src.api.v3.core.base_crud import CRUDBase


class ScheduledReportCRUD(CRUDBase[ScheduledReport, dict, dict]):
    model = ScheduledReport
    keyword_fields = ("name", "report_type")
    default_order_by = "id"


class ReportHistoryCRUD(CRUDBase[ReportHistory, dict, dict]):
    model = ReportHistory
    keyword_fields = ("report_name", "report_type")
    #: 历史以生成时间为序（新在前）
    default_order_by = "generated_at"


scheduled_report_crud = ScheduledReportCRUD()
report_history_crud = ReportHistoryCRUD()
