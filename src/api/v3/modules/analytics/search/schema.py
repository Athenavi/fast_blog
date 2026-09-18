"""search_analytics 模块的响应模型"""

from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class PopularKeyword(SchemaBase):
    keyword: str
    count: int = 0
    avg_results: float = 0.0


class ZeroResultKeyword(SchemaBase):
    keyword: str
    count: int = 0


class SearchTrendPoint(SchemaBase):
    day: str
    searches: int = 0
    zero_result: int = 0


class SearchTrendOut(SchemaBase):
    days: int
    points: List[SearchTrendPoint] = Field(default_factory=list)


class SearchSummaryOut(SchemaBase):
    total_searches: int = 0
    unique_keywords: int = 0
    zero_result_searches: int = 0
    zero_result_rate: Optional[float] = None
