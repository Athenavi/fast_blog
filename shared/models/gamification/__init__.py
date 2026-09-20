"""
gamification 子模块 - 模型定义（T5-11 批次 12：积分与勋章）
手写模型，写法对齐代码生成器产物。

> v2 的积分 / 勋章是**进程内内存单例**（`services/advanced_features/`），重启即失、
> 多 worker 各一份；且勋章统计函数 `_get_user_stats` **直接返回全 0**（真查询被注释），
> 导致 `check-and-award` 永不授予。这里是真表 + 真实统计源。
"""
from .badge_definition import BadgeDefinition
from .points_rule import PointsRule
from .points_transaction import PointsTransaction
from .user_badge import UserBadge
from .user_points import UserPoints

__all__ = [
    'BadgeDefinition',
    'PointsRule',
    'PointsTransaction',
    'UserBadge',
    'UserPoints',
]
