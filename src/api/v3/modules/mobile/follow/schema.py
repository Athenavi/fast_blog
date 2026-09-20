"""follow 模块的请求 / 响应模型

列表项形状与 v2 对齐（``{user, created_at}``），但**多了两个标记**：

  - ``is_following``：**当前登录者**是否关注了该用户（匿名时恒 ``false``）
  - ``is_mutual``：是否互相关注（同样只在登录时有意义）

v2 完全没有这两个标记，前端只能自己再发一轮请求。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class FollowUserBrief(SchemaBase):
    """关注关系里的用户摘要（不含权限/管理字段）"""

    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = Field(default=None, description="注册时间")
    #: 当前登录者是否关注了 TA
    is_following: bool = False
    #: 与当前登录者是否互相关注
    is_mutual: bool = False


class FollowItem(SchemaBase):
    """一条关注关系（粉丝 / 关注列表项）"""

    user: FollowUserBrief
    created_at: Optional[datetime] = Field(default=None, description="关注 / 被关注时间")


class FollowStats(SchemaBase):
    """某个用户的关注概览"""

    user_id: int
    follower_count: int = 0
    following_count: int = 0
    #: 当前登录者是否关注了 TA
    is_following: bool = False
    #: 是否互相关注
    is_mutual: bool = False
