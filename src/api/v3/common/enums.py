"""V3 通用枚举

结构对齐 FastApiAdmin `app/common/enums.py`，只保留通用项；业务枚举放在各模块自己的
``enums.py`` 或 schema 内。
"""

from enum import Enum, IntEnum


class StatusEnum(IntEnum):
    """启用状态（0 禁用 / 1 启用）"""

    DISABLED = 0
    ENABLED = 1


class YesNoEnum(IntEnum):
    """是否标记"""

    NO = 0
    YES = 1


class SortOrderEnum(str, Enum):
    """排序方向"""

    ASC = "asc"
    DESC = "desc"


class ReviewStatusEnum(IntEnum):
    """审核状态（评论 / 投稿等内容复用）"""

    PENDING = 0
    APPROVED = 1
    REJECTED = 2
