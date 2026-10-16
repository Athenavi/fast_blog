"""help 模块的请求模型

写端点（``POST /help/topic``）刻意收**原始 dict**（见 controller 注释），因此这里的模型
主要用于 OpenAPI 文档展示与字段说明，避免 pydantic 静默丢弃未知字段。
"""

from typing import Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class HelpTopicUpsert(SchemaBase):
    """新增 / 覆盖一条自定义帮助（同 ``page_key`` 覆盖默认或既有自定义条目）"""

    page_key: str = Field(min_length=1, max_length=100, description="页面标识，如 article_editor")
    title: str = Field(min_length=1, max_length=200, description="帮助标题")
    content: str = Field(min_length=1, max_length=200_000, description="帮助内容（HTML）")
    tags: List[str] = Field(default_factory=list, description="检索标签")
    language: Optional[str] = Field(default="zh_CN", description="zh_CN / en_US")
    related_links: List[Dict[str, str]] = Field(
        default_factory=list, description="相关链接 [{title, url}]"
    )
