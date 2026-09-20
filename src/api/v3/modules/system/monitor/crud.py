"""monitor 模块的数据访问层（唯一 DB 访问点）

模块原有部分（server / online）不落表，只读 ``user_sessions``；
下面三个 CRUD 服务于批次 10 新增的**告警 / 指标 / SLA** 三组能力
（表 ``monitoring_alerts`` / ``monitoring_metrics`` / ``sla_reports``）。
"""

from shared.models.monitoring import MonitoringAlert, MonitoringMetric, SLAReport
from src.api.v3.core.base_crud import CRUDBase


class MonitoringAlertCRUD(CRUDBase[MonitoringAlert, dict, dict]):
    model = MonitoringAlert
    keyword_fields = ("title", "message", "source", "metric_name")
    #: 告警以创建时间为序（新在前）
    default_order_by = "created_at"


class MonitoringMetricCRUD(CRUDBase[MonitoringMetric, dict, dict]):
    model = MonitoringMetric
    keyword_fields = ("metric_name", "metric_type")
    #: 指标是时序数据，按时间倒序
    default_order_by = "timestamp"


class SLAReportCRUD(CRUDBase[SLAReport, dict, dict]):
    model = SLAReport
    default_order_by = "period_end"


monitoring_alert_crud = MonitoringAlertCRUD()
monitoring_metric_crud = MonitoringMetricCRUD()
sla_report_crud = SLAReportCRUD()
