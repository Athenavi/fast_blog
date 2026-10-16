"""analytics/tracking 模块请求模型（埋点上报）

上报走**可选登录**（访客浏览也要能记），所以字段尽量宽松但都限长，避免脏数据写库报错。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class PageViewTrackRequest(SchemaBase):
    """页面浏览上报"""

    page_url: str = Field(min_length=1, max_length=500, description="页面 URL（建议相对路径）")
    page_title: Optional[str] = Field(default=None, max_length=500)
    referrer: Optional[str] = Field(default=None, max_length=500, description="来源页；空表示直接访问")
    session_id: Optional[str] = Field(
        default=None, max_length=255, description="前端生成的会话 ID（同一会话复用，用于会话统计）"
    )


class EventTrackRequest(SchemaBase):
    """行为事件上报（view/like/share/bookmark/comment/click/scroll/follow/purchase…）"""

    activity_type: str = Field(min_length=1, max_length=100, description="事件类型（稳定枚举）")
    target_type: Optional[str] = Field(default=None, max_length=50, description="目标类型，如 article")
    target_id: Optional[int] = Field(default=None, ge=1, description="目标 ID，如文章 ID")
    details: Optional[str] = Field(default=None, max_length=255, description="附加说明")


class SearchTrackRequest(SchemaBase):
    """搜索记录上报"""

    keyword: str = Field(min_length=1, max_length=255)
    results_count: int = Field(default=0, ge=0, le=1_000_000, description="本次搜索命中结果数")


class AdImpressionTrackRequest(SchemaBase):
    """广告曝光上报"""

    ad_id: int = Field(ge=1)
    page_url: Optional[str] = Field(default=None, max_length=500)


class AdClickTrackRequest(SchemaBase):
    """广告点击上报"""

    ad_id: int = Field(ge=1)
    referrer: Optional[str] = Field(default=None, max_length=500)
