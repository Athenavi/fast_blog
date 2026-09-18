"""V3 权限包（对齐 FastApiAdmin 的认证 / 授权模型）

模块划分：

| 模块 | 职责 |
|---|---|
| `constants.py` | 权限码与数据范围常量（唯一真相），**不做分隔符转换** |
| `cache.py` | 三层缓存：request.state → 进程内存 LRU → Redis |
| `loader.py` | 权限码加载（PostgreSQL 递归 CTE 解析角色继承） |
| `control.py` | `AuthPermission`：ANY 语义 + 通配 + 单点 superuser bypass + fail-closed |
| `invalidate.py` | 失效与跨进程广播（覆盖所有权限变更点） |

> 数据范围（权限组）过滤将在后续阶段以 `scope.py` 加入本包。
"""

from src.api.v3.core.permission.cache import memory_cache
from src.api.v3.core.permission.constants import (
    DATA_SCOPE_ALL,
    DATA_SCOPE_CUSTOM,
    DATA_SCOPE_GROUP_AND_CHILD,
    DATA_SCOPE_LABELS,
    DATA_SCOPE_SELF,
    VALID_DATA_SCOPES,
    WILDCARD_CODES,
    normalize_code,
)
from src.api.v3.core.permission.control import AuthControl, AuthPermission
from src.api.v3.core.permission.invalidate import (
    cache_stats,
    invalidate_all,
    invalidate_user,
    start_invalidate_subscriber,
)
from src.api.v3.core.permission.loader import load_codes, load_codes_from_db

__all__ = [
    # 常量
    "DATA_SCOPE_SELF",
    "DATA_SCOPE_GROUP_AND_CHILD",
    "DATA_SCOPE_ALL",
    "DATA_SCOPE_CUSTOM",
    "VALID_DATA_SCOPES",
    "DATA_SCOPE_LABELS",
    "WILDCARD_CODES",
    "normalize_code",
    # 控制
    "AuthPermission",
    "AuthControl",
    # 加载与缓存
    "load_codes",
    "load_codes_from_db",
    "memory_cache",
    # 失效
    "invalidate_user",
    "invalidate_all",
    "start_invalidate_subscriber",
    "cache_stats",
]
