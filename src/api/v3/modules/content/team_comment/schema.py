"""team_comment 模块的请求 / 响应模型（Pydantic v2）"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: ``team_comments.mentions`` 列宽（``String(500)``）—— 写入前据此裁剪
MENTIONS_MAX_LENGTH = 500
#: 评论正文长度上限
TEXT_MAX_LENGTH = 5000


class TeamCommentCreate(SchemaBase):
    """发表团队评论（``text`` 入库前一律 ``html.escape``）"""

    content_type: str = Field(min_length=1, max_length=50, description="内容对象类型，如 article / page")
    content_id: int = Field(description="内容对象 ID")
    text: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH, description="评论正文")
    parent_id: Optional[int] = Field(default=None, description="父评论 ID（支持嵌套回复）")
    mentions: Optional[list[int]] = Field(default=None, description="@ 提及的用户 ID 列表")


class TeamCommentUpdate(SchemaBase):
    """修改评论正文"""

    text: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH)


class TeamCommentOut(SchemaBase):
    """团队评论输出（``children`` 用于线程树；``mentions`` 是解析后的整数列表）"""

    id: int
    content_type: Optional[str] = None
    content_id: Optional[int] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    parent_id: Optional[int] = None
    text: Optional[str] = None
    mentions: list[int] = Field(default_factory=list)
    is_resolved: bool = False
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: list["TeamCommentOut"] = Field(default_factory=list)


TeamCommentOut.model_rebuild()


class AuthorCountOut(SchemaBase):
    """按作者的评论计数"""

    author_id: int
    count: int


class TeamCommentStatisticsOut(SchemaBase):
    """团队评论统计"""

    total_comments: int = 0
    resolved_comments: int = 0
    unresolved_comments: int = 0
    by_author: list[AuthorCountOut] = Field(default_factory=list)
