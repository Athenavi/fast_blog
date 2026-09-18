"""monitor 模块的请求/响应模型"""

from typing import Any, Dict, List

from pydantic import Field

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
