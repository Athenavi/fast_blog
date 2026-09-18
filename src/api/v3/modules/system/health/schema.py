"""health 模块的响应模型"""

from typing import Dict

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class HealthPayload(SchemaBase):
    """健康探针载荷"""

    status: str = Field(description="ok / degraded")
    service: str = Field(description="服务标识")
    version: str = Field(description="版本号")
    environment: str = Field(description="运行环境")
    checks: Dict[str, str] = Field(default_factory=dict, description="各依赖检查结果")
