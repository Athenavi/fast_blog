"""health 模块的响应模型"""

from typing import Dict, Literal, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class HealthPayload(SchemaBase):
    """健康探针载荷"""

    status: str = Field(description="ok / degraded")
    service: str = Field(description="服务标识")
    version: str = Field(description="版本号")
    environment: str = Field(description="运行环境")
    checks: Dict[str, str] = Field(default_factory=dict, description="各依赖检查结果")


class WebVitalSample(SchemaBase):
    """RUM 上报的单条 Web Vitals 样本

    字段与前端 ``composables/useWebVitals.ts`` 的 ``VitalSample`` 一一对应，
    因为前端是用 ``navigator.sendBeacon`` 直接把这批样本原样发过来的（数组 body）。
    """

    name: Literal["LCP", "INP", "CLS", "FCP", "TTFB"] = Field(description="指标名")
    value: float = Field(ge=0, le=3_600_000, description="指标值（毫秒；CLS 为无量纲比例）")
    rating: Optional[Literal["good", "needs-improvement", "poor"]] = Field(
        default=None, description="web-vitals 给出的评级"
    )
    id: Optional[str] = Field(default=None, max_length=64, description="web-vitals 指标 id")
    ts: Optional[int] = Field(default=None, ge=0, description="客户端时间戳（毫秒）")
    path: Optional[str] = Field(default=None, max_length=512, description="页面路径（不含 query）")
    sessionId: Optional[str] = Field(default=None, max_length=64, description="前端会话 id")
