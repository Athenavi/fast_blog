"""badge 模块的请求 / 响应模型

**统计口径**（v2 的 `_get_user_stats` 直接返回全 0，真查询被注释掉了）——这里全部取自真实表：

  - ``article_count``      该用户**已发布**的文章数（``articles.user`` + ``status=1``）
  - ``max_article_likes``  单篇最高获赞（``articles.likes`` 最大值）
  - ``follower_count``     粉丝数（``user_follows.following``，批次 11 新建的表）
  - ``comment_count``      评论数（``comments.user``）
  - ``like_received``      累计获赞（``sum(articles.likes)``）
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 勋章条件类型白名单（与统计口径一一对应）
CONDITION_TYPES: tuple[str, ...] = (
    "article_count",
    "max_article_likes",
    "follower_count",
    "comment_count",
    "like_received",
)


class BadgeOut(SchemaBase):
    id: int
    badge_key: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    points_reward: int = 0
    condition_type: Optional[str] = None
    condition_value: int = 0
    is_manual: bool = False
    is_active: bool = True
    sort_order: int = 0


class UserBadgeOut(SchemaBase):
    """我（或某人）已获得的勋章 —— 定义信息一并带上，前端不用二次查询"""

    badge_key: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    points_reward: int = 0
    awarded_at: Optional[datetime] = None
    awarded_by: Optional[int] = None


class BadgeProgressOut(SchemaBase):
    badge_key: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    condition_type: Optional[str] = None
    condition_value: int = 0
    current_value: int = 0
    achieved: bool = False
    progress_percent: float = 0.0
    awarded: bool = False


class BadgeAwardRequest(SchemaBase):
    user_id: int
    badge_key: str = Field(min_length=1, max_length=50)


class BadgeCheckResult(SchemaBase):
    """``check-and-award`` 的结果：本次新授予了哪些 + 当前全部已获"""

    awarded: list[UserBadgeOut] = Field(default_factory=list)
    skipped_manual: list[str] = Field(default_factory=list, description="仅可手工授予、已跳过")
    progress: list[BadgeProgressOut] = Field(default_factory=list)


class BadgeStatsOut(SchemaBase):
    total_definitions: int = 0
    active_definitions: int = 0
    total_awarded: int = 0
    by_category: list[dict] = Field(default_factory=list)
    top_badges: list[dict] = Field(default_factory=list)
