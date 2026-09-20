"""report 模块的请求 / 响应模型

报表内容本身是**结构随类型变化**的 dict（真实聚合结果），这里不强行建模，
只对入参与"定时报表 / 报表历史"两个实体建模。
"""

import json
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase

#: 可生成的报表类型（与 v2 的 report_type 取值对齐）
REPORT_TYPES: tuple[str, ...] = ("content", "user-activity", "traffic", "custom")
#: 定时执行频率
REPORT_FREQUENCIES: tuple[str, ...] = ("daily", "weekly", "monthly")
#: 导出格式
REPORT_FORMATS: tuple[str, ...] = ("json", "csv")
#: 自定义报表可选的指标块
CUSTOM_METRICS: tuple[str, ...] = ("content", "users", "traffic", "engagement")
#: 天数范围（与 v2 一致）
MIN_DAYS = 7
MAX_DAYS = 90


class CustomReportRequest(SchemaBase):
    metrics: list[str] = Field(min_length=1, description="要包含的指标块")
    days: int = Field(default=30, ge=MIN_DAYS, le=MAX_DAYS)
    filters: Optional[dict] = Field(default=None, description="附加过滤条件（原样回显，便于前端定位）")


class ReportExportRequest(SchemaBase):
    report_type: str = Field(description="content / user-activity / traffic / custom")
    format: str = Field(default="json", description="json / csv")
    days: int = Field(default=30, ge=MIN_DAYS, le=MAX_DAYS)
    metrics: Optional[list[str]] = Field(default=None, description="report_type=custom 时必填")


# ---------------------------------------------------------------- 定时报表
class ScheduledReportCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    report_type: str = Field(min_length=1, max_length=50)
    frequency: str = Field(default="daily", max_length=20)
    metrics: Optional[list[str]] = Field(default=None, description="custom 类型需要")
    days: int = Field(default=30, ge=MIN_DAYS, le=MAX_DAYS)
    export_format: str = Field(default="json", max_length=10)
    is_active: bool = True


class ScheduledReportUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    report_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    frequency: Optional[str] = Field(default=None, max_length=20)
    metrics: Optional[list[str]] = None
    days: Optional[int] = Field(default=None, ge=MIN_DAYS, le=MAX_DAYS)
    export_format: Optional[str] = Field(default=None, max_length=10)
    is_active: Optional[bool] = None


class ScheduledReportOut(SchemaBase):
    id: int
    name: Optional[str] = None
    report_type: Optional[str] = None
    frequency: Optional[str] = None
    metrics: Optional[list[str]] = None
    days: int = 30
    export_format: Optional[str] = None
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("metrics", mode="before")
    @classmethod
    def _parse_metrics(cls, value: object) -> object:
        """库列是 JSON 字符串，反序列化为列表"""
        if isinstance(value, str) and value:
            try:
                parsed = json.loads(value)
            except ValueError:
                return None
            return parsed if isinstance(parsed, list) else None
        return value


# ---------------------------------------------------------------- 报表历史
class ReportHistoryOut(SchemaBase):
    """列表用：**不含 ``content``**（报表正文可能很大，只在下载接口返回）"""

    id: int
    scheduled_report_id: Optional[int] = None
    report_name: Optional[str] = None
    report_type: Optional[str] = None
    format: Optional[str] = None
    generated_at: Optional[datetime] = None
