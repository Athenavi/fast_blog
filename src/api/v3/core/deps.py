"""V3 依赖注入集合

结构对齐 FastApiAdmin `app/core/dependencies.py`，实现接在 fast_blog 既有能力上：

  - 会话：``src/utils/database/unified_manager.get_db_session``
  - 认证：``src/auth/auth_deps.get_current_user`` / ``admin_required``
  - 鉴权：``src/api/v3/core/permission``（三层缓存 + 通配 + 单点 superuser bypass + fail-closed）

用法::

    from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep

    @router.get("/list")
    async def list_users(
        page: PageDep,
        db: DBSession,
        _: CurrentUser,
        _perm=AuthControl("user:view"),
    ):
        ...

权限码约定：

  - 与后端 ``capabilities.code`` **完全一致**（``resource:action``）
  - 比较时**不做任何分隔符转换**（历史实现把冒号换成点号再比较，导致校验恒失败）
  - 多个权限码为 **ANY 语义**（任一命中即通过），与官方 ``AuthPermission`` 一致
"""

from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.api.v3.common.request import PageQuery
from src.api.v3.core.permission.control import AuthControl, AuthPermission
from src.auth.auth_deps import admin_required, get_current_user, jwt_optional_dependency
from src.utils.database.unified_manager import get_db_session

# ---------- 会话 / 分页 ----------
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
PageDep = Annotated[PageQuery, Depends()]

# ---------- 身份 ----------
CurrentUser = Annotated[UserModel, Depends(get_current_user)]
AdminUser = Annotated[UserModel, Depends(admin_required)]
#: 可选身份：匿名返回 None（媒体文件等公开资源端点用）
OptionalUser = Annotated[Optional[UserModel], Depends(jwt_optional_dependency)]

__all__ = [
    "DBSession",
    "PageDep",
    "CurrentUser",
    "AdminUser",
    "OptionalUser",
    "AuthControl",
    "AuthPermission",
]
