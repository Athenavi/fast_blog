"""ad 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class AdPlacementCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern="^[a-z0-9_-]+$", description="广告位代码（唯一）")
    description: Optional[str] = None
    position: str = Field(default="sidebar", max_length=50, description="位置 header/sidebar/footer/content")
    width: Optional[int] = Field(default=None, ge=0)
    height: Optional[int] = Field(default=None, ge=0)
    is_active: bool = True


class AdPlacementUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, min_length=1, max_length=50, pattern="^[a-z0-9_-]+$")
    description: Optional[str] = None
    position: Optional[str] = Field(default=None, max_length=50)
    width: Optional[int] = Field(default=None, ge=0)
    height: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class AdPlacementOut(SchemaBase):
    id: int
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    position: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    content: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    link_url: Optional[str] = Field(default=None, max_length=500)
    alt_text: Optional[str] = Field(default=None, max_length=255)
    ad_type: str = Field(default="image", max_length=30, description="image/text/code")
    placement_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    cost_per_click: Optional[float] = None
    cost_per_impression: Optional[float] = None
    is_active: bool = True
    priority: int = Field(default=0, ge=0)
    target_audience: Optional[str] = Field(default=None, max_length=100)
    device_targeting: Optional[str] = Field(default=None, max_length=100)
    geo_targeting: Optional[str] = Field(default=None, max_length=100)


class AdUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    link_url: Optional[str] = Field(default=None, max_length=500)
    alt_text: Optional[str] = Field(default=None, max_length=255)
    ad_type: Optional[str] = Field(default=None, max_length=30)
    placement_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    cost_per_click: Optional[float] = None
    cost_per_impression: Optional[float] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0)
    target_audience: Optional[str] = Field(default=None, max_length=100)
    device_targeting: Optional[str] = Field(default=None, max_length=100)
    geo_targeting: Optional[str] = Field(default=None, max_length=100)


class AdOut(SchemaBase):
    id: int
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    alt_text: Optional[str] = None
    ad_type: Optional[str] = None
    placement_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    click_count: int = 0
    impression_count: int = 0
    budget: Optional[float] = None
    cost_per_click: Optional[float] = None
    cost_per_impression: Optional[float] = None
    is_active: bool = True
    priority: int = 0
    target_audience: Optional[str] = None
    device_targeting: Optional[str] = None
    geo_targeting: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdStatsOut(SchemaBase):
    total_ads: int = 0
    active_ads: int = 0
    total_clicks: int = 0
    total_impressions: int = 0
    total_budget: float = 0.0
