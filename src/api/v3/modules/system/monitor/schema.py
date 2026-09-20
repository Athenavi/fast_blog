"""monitor 模块的请求/响应模型"""

import json
from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field, field_validator

from src.api.v3.core.base_schema import SchemaBase


class CpuInfo(SchemaBase):
    """CPU 信息"""

    count: int = Field(description="逻辑核数")
    percent: float = Field(description="总体使用率（%）")
    load_avg: List[float] = Field(default_factory=list, description="1/5/15 分钟负载；Windows 无此指标时为空")


class MemoryInfo(SchemaBase):
    """内存信息（字节）"""

    total: int = Field(description="总内存")
    used: int = Field(description="已用内存")
    percent: float = Field(description="使用率（%）")


class DiskInfo(SchemaBase):
    """单个挂载点"""

    device: str = Field(description="设备")
    mountpoint: str = Field(description="挂载点")
    fstype: str = Field(default="", description="文件系统类型")
    total: int = Field(description="总容量")
    used: int = Field(description="已用容量")
    percent: float = Field(description="使用率（%）")


class ProcessInfo(SchemaBase):
    """当前 API 进程"""

    pid: int = Field(description="进程 ID")
    rss: int = Field(description="常驻内存（字节）")
    threads: int = Field(default=0, description="线程数")


class ServerInfoPayload(SchemaBase):
    """服务器信息"""

    platform: str = Field(description="操作系统")
    hostname: str = Field(description="主机名")
    python_version: str = Field(description="Python 版本")
    boot_time: str = Field(description="启动时间（ISO8601）")
    uptime_seconds: int = Field(description="已运行秒数")
    cpu: CpuInfo
    memory: MemoryInfo
    disks: List[DiskInfo] = Field(default_factory=list, description="磁盘列表")
    process: ProcessInfo


class OnlineSessionItem(SchemaBase):
    """一条在线会话（**不含 token**）"""

    id: int = Field(description="会话主键")
    user_id: int = Field(description="用户 ID")
    device_info: str | None = Field(default=None, description="设备 / User-Agent")
    ip_address: str | None = Field(default=None, description="IP")
    location: str | None = Field(default=None, description="地理位置")
    last_activity: str | None = Field(default=None, description="最后活动时间")
    created_at: str | None = Field(default=None, description="登录时间")


class OnlineStatsPayload(SchemaBase):
    """在线统计"""

    active_sessions: int = Field(description="活跃会话总数")
    recent_sessions: int = Field(description="窗口期内有活动的会话数")
    unique_users: int = Field(description="去重用户数")
    window_seconds: int = Field(description="“在线”判定窗口（秒）")


class MonitorOverviewPayload(SchemaBase):
    """系统总览聚合（首屏一次拿全）"""

    server: Dict[str, Any] = Field(default_factory=dict, description="服务器信息")
    online: Dict[str, Any] = Field(default_factory=dict, description="在线统计")


# ================================================================ 告警 / 指标 / SLA（批次 10）

#: 告警严重程度
ALERT_SEVERITIES: tuple[str, ...] = ("info", "warning", "error", "critical")
#: 指标时序聚合的时间桶
METRIC_BUCKETS: tuple[str, ...] = ("minute", "hour", "day")


def _parse_int_list(value: object) -> object:
    """``notified_users`` 列是 JSON 字符串，出参还原为列表（脏数据回退 None）"""
    if value is None or isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _parse_labels(value: object) -> object:
    """``labels`` 列是 JSON 字符串，出参还原为对象"""
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


class AlertCreate(SchemaBase):
    alert_type: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1)
    severity: str = Field(default="warning", max_length=20)
    title: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=255)
    metric_name: str | None = Field(default=None, max_length=100)
    metric_value: float | None = None
    threshold: float | None = None
    notified_users: List[int] | None = None


class AlertUpdate(SchemaBase):
    alert_type: str | None = Field(default=None, min_length=1, max_length=50)
    message: str | None = Field(default=None, min_length=1)
    severity: str | None = Field(default=None, max_length=20)
    title: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=255)
    metric_name: str | None = Field(default=None, max_length=100)
    metric_value: float | None = None
    threshold: float | None = None
    is_resolved: bool | None = None
    notified_users: List[int] | None = None


class AlertOut(SchemaBase):
    id: int
    alert_type: str | None = None
    severity: str | None = None
    title: str | None = None
    message: str | None = None
    source: str | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    threshold: float | None = None
    is_resolved: bool = False
    resolved_at: datetime | None = None
    notified_users: List[int] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("notified_users", mode="before")
    @classmethod
    def _parse_notified(cls, value: object) -> object:
        return _parse_int_list(value)


class MetricCreate(SchemaBase):
    metric_name: str = Field(min_length=1, max_length=100)
    metric_value: float
    metric_type: str | None = Field(default=None, max_length=50, description="cpu / memory / disk / request …")
    labels: Dict[str, Any] | None = None
    timestamp: datetime | None = Field(default=None, description="缺省为当前时间")
    site_id: int | None = None


class MetricOut(SchemaBase):
    id: int
    metric_name: str | None = None
    metric_value: float | None = None
    metric_type: str | None = None
    labels: Dict[str, Any] | None = None
    timestamp: datetime | None = None
    site_id: int | None = None

    @field_validator("labels", mode="before")
    @classmethod
    def _parse_labels_field(cls, value: object) -> object:
        return _parse_labels(value)


class SLACreate(SchemaBase):
    license_id: int
    period_start: datetime
    period_end: datetime
    target_percentage: float = Field(default=99.9, ge=0, le=100)
    uptime_percentage: float | None = Field(
        default=None, ge=0, le=100, description="不传则按周期内 critical 告警时长自动计算"
    )
    downtime_minutes: int | None = Field(default=None, ge=0)


class SLAComputeRequest(SchemaBase):
    license_id: int
    period_start: datetime
    period_end: datetime
    target_percentage: float = Field(default=99.9, ge=0, le=100)


class SLAUpdate(SchemaBase):
    target_percentage: float | None = Field(default=None, ge=0, le=100)
    uptime_percentage: float | None = Field(default=None, ge=0, le=100)
    downtime_minutes: int | None = Field(default=None, ge=0)
    period_start: datetime | None = None
    period_end: datetime | None = None


class SLAOut(SchemaBase):
    id: int
    license_id: int | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    uptime_percentage: float | None = None
    target_percentage: float | None = None
    is_compliant: bool = False
    downtime_minutes: int = 0
    total_minutes: int | None = None
    created_at: datetime | None = None
    checked_at: datetime | None = None
