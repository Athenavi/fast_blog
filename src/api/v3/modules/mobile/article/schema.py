"""mobile/article 的请求模型（用户投稿）

安全设计：**只暴露作者端应当控制的字段**。
`status`、`is_featured`、`is_sticky`、`hidden`、`sort_order`、`scheduled_publish_at`
这些**管理字段一律不出现在请求模型里**，由 service 强制置为草稿与默认值——
否则前台用户就能自行发布/置顶/加精。

**例外：`is_vip_only` / `required_vip_level`（2026-09-20 批次 16 放开）** ——
这两个是**内容属性**而不是发布状态：作者可以把自己的稿件标为"仅 VIP 可见"并指定所需等级
（后台仍有 `article:edit` 可以改回来）。`status` 依然被强制为草稿，
"投稿 → 审核 → 发布"的分离不变。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 单个 VIP 等级上限（与后台 article 的 required_vip_level 一致）
MAX_VIP_LEVEL = 9


class MobileArticleCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, description="正文；写入 article_content")
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    language_code: str = Field(default="zh-CN")
    is_vip_only: bool = Field(default=False, description="仅 VIP 可见（内容属性，可自助设置）")
    required_vip_level: int = Field(default=0, ge=0, le=MAX_VIP_LEVEL, description="所需 VIP 等级（0 表示不限等级）")


class MobileArticleUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    excerpt: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None)
    cover_image: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = None
    tags: Optional[list[str]] = None
    language_code: Optional[str] = None
    is_vip_only: Optional[bool] = Field(default=None, description="仅 VIP 可见")
    required_vip_level: Optional[int] = Field(default=None, ge=0, le=MAX_VIP_LEVEL)


class MobileArticleQuery(SchemaBase):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[int] = Field(default=None, description="0 草稿 / 1 已发布")
    keyword: Optional[str] = None
