"""third_party_publish 模块的请求 / 响应模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


# ---------------------------------------------------------------- 渠道
class PublishChannelCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100, description="渠道名（如「我的公众号」）")
    platform: str = Field(
        min_length=1, max_length=32, description="平台标识（必须是适配器注册表里的 key）"
    )
    endpoint: Optional[str] = Field(
        default=None, max_length=255, description="平台 API 基址覆盖（自建网关用）"
    )
    credentials: dict[str, Any] = Field(
        default_factory=dict, description="凭据字典（落库前 AES-256-GCM 加密，永不回传）"
    )
    is_active: bool = True


class PublishChannelUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    endpoint: Optional[str] = Field(default=None, max_length=255)
    credentials: Optional[dict[str, Any]] = Field(
        default=None, description="凭据：**不传或传空对象表示保持原值**"
    )
    is_active: Optional[bool] = None


class PublishChannelOut(SchemaBase):
    id: int
    name: str
    platform: str
    endpoint: Optional[str] = None
    is_active: bool = True
    #: 是否已配置凭据（密文永不回传）
    has_credentials: bool = False
    #: 该平台是否已注册适配器（False = 底座就绪、平台适配器待接入）
    adapter_ready: bool = False
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------- 日志
class PublishLogOut(SchemaBase):
    id: int
    task_id: int
    status: str
    message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------- 任务
class PublishTaskCreate(SchemaBase):
    article_id: int = Field(gt=0, description="要发布的文章 ID")
    channel_id: int = Field(gt=0, description="目标渠道 ID")


class PublishTaskOut(SchemaBase):
    id: int
    article_id: int
    channel_id: int
    status: str = "pending"
    attempts: int = 0
    last_error: Optional[str] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    created_by: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #: 列表展示用（service 填充，不是表字段）
    article_title: Optional[str] = None
    channel_name: Optional[str] = None
    channel_platform: Optional[str] = None


class PublishTaskDetailOut(PublishTaskOut):
    """任务详情的**字段说明**（实际输出由 service 组装：额外带载荷快照与最近日志）

    这里只是类型占位 —— 载荷在库里是 TEXT（JSON 串），不能直接 ``model_validate``，
    因此 service 用 ``_task_out()`` 之后再补 ``payload`` / ``logs`` 两个键。
    """

    payload: Optional[dict[str, Any]] = None
    logs: list[PublishLogOut] = Field(default_factory=list)


# ---------------------------------------------------------------- 平台
class PublishPlatformOut(SchemaBase):
    platform: str
    display_name: str
