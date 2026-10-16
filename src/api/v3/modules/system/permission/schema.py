"""permission 模块的请求 / 响应模型"""

from typing import Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class CapabilityOut(SchemaBase):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    is_active: bool = True


class CapabilityGroup(SchemaBase):
    resource_type: str
    capabilities: List[CapabilityOut] = Field(default_factory=list)


class PermissionCheckRequest(SchemaBase):
    codes: List[str] = Field(min_length=1, description="待校验的权限码列表")


class PermissionCheckResult(SchemaBase):
    granted: Dict[str, bool] = Field(default_factory=dict)
    all_granted: bool = False
    missing: List[str] = Field(default_factory=list)


class CacheStatsOut(SchemaBase):
    memory: Dict = Field(default_factory=dict)
    redis: Dict = Field(default_factory=dict)
    detail: Optional[Dict] = None
