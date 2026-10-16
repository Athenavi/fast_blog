"""export 模块的请求模型"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ExportPreviewRequest(SchemaBase):
    """导出预览请求：指定资源并取前 ``limit`` 行

    ``keyword`` / ``start`` / ``end`` 与 CSV 导出端点保持同一套过滤语义
    （关键词命中资源的 ``search_fields``，时间范围命中资源的 ``time_field``）。
    """

    resource: str = Field(
        min_length=1, max_length=50, description="导出资源名（见 /export/templates）"
    )
    limit: int = Field(default=20, ge=1, le=200, description="预览行数")
    keyword: Optional[str] = Field(default=None, max_length=200, description="关键词模糊过滤")
    start: Optional[datetime] = Field(default=None, description="时间范围起点（含）")
    end: Optional[datetime] = Field(default=None, description="时间范围终点（含）")

    def filters_dict(self) -> Dict[str, Any]:
        """整理成 service 层 ``filters`` 结构"""
        return {"keyword": self.keyword, "start": self.start, "end": self.end}
