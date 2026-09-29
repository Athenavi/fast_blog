"""maintenance 模块的请求模型"""

from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MaintenanceEnableRequest(SchemaBase):
    """开启维护模式（可选覆盖提示语 / 白名单 / Retry-After）"""

    message: Optional[str] = Field(default=None, max_length=500)
    whitelist_ips: Optional[List[str]] = Field(default=None, description="维护期间仍可访问的 IP")
    retry_after: Optional[int] = Field(default=None, ge=0, le=604800, description="秒")


class MaintenanceMessageRequest(SchemaBase):
    message: str = Field(min_length=1, max_length=500)


class MaintenanceScheduleRequest(SchemaBase):
    """定时维护窗口（到点自动生效 / 失效，无需再改配置）"""

    scheduled_start: str = Field(min_length=1, max_length=50, description="ISO 时间")
    scheduled_end: str = Field(min_length=1, max_length=50, description="ISO 时间，须晚于 start")
    message: Optional[str] = Field(default=None, max_length=500)


class MaintenanceWhitelistRequest(SchemaBase):
    ip: str = Field(min_length=1, max_length=64)
