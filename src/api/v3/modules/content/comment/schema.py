"""comment 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from src.api.v3.core.base_schema import SchemaBase


class CommentPublicOut(SchemaBase):
    """公开字段（不含邮箱 / IP / UA）"""

    id: int
    article_id: int
    parent_id: Optional[int] = None
    user_id: Optional[int] = None
    content: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    likes: int = 0
    created_at: Optional[datetime] = None
    children: List["CommentPublicOut"] = Field(default_factory=list)


CommentPublicOut.model_rebuild()


class CommentAdminOut(SchemaBase):
    """管理端字段（含隐私与审核信息）"""

    id: int
    article_id: int
    parent_id: Optional[int] = None
    user_id: Optional[int] = None
    content: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_url: Optional[str] = None
    author_ip: Optional[str] = None
    user_agent: Optional[str] = None
    is_approved: bool = False
    likes: int = 0
    spam_score: Optional[float] = None
    spam_reasons: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CommentCreate(SchemaBase):
    """提交评论（登录用户可省略 author_*，由后端从账号补齐）"""

    article_id: int
    content: str = Field(min_length=1, max_length=5000)
    parent_id: Optional[int] = None
    author_name: Optional[str] = Field(default=None, max_length=100)
    author_email: Optional[EmailStr] = None
    author_url: Optional[str] = Field(default=None, max_length=500)


class CommentUpdate(SchemaBase):
    content: str = Field(min_length=1, max_length=5000)


class CommentBatchDeleteRequest(SchemaBase):
    ids: List[int] = Field(min_length=1)
