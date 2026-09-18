"""V3 依赖注入集合

结构对齐 FastApiAdmin `app/core/dependencies.py`（``AuthControl`` / ``CurrentUser`` / ``Pagination``
风格），实现接到 fast_blog 既有能力上：

  - 会话：``src/utils/database/unified_manager.get_db_session``（异步，单例管理器）
  - 认证：``src/auth/auth_deps.get_current_user`` / ``admin_required``
  - 鉴权：``src/api/v3/_permission.Permission``（三重缓存 + superuser bypass，fail-closed）

用法::

    from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep

    @router.get("/list")
    async def list_users(
        page: PageDep,
        db: DBSession,
        _: CurrentUser,
        _perm=AuthControl("system.user.list"),
    ):
        ...

权限码约定：点号形式（``system.user.list``）。``Permission`` 内部会把冒号归一化为点号，
但新代码统一写点号，避免依赖归一化行为。
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.api.v3._permission import Permission
from src.api.v3.common.request import PageQuery
from src.auth.auth_deps import admin_required, get_current_user
from src.utils.database.unified_manager import get_db_session

# ---------- 会话 / 分页 ----------
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
PageDep = Annotated[PageQuery, Depends()]

# ---------- 身份 ----------
CurrentUser = Annotated[UserModel, Depends(get_current_user)]
AdminUser = Annotated[UserModel, Depends(admin_required)]


def AuthControl(*codes: str):
    """权限校验依赖工厂（多权限为 AND 语义）

    ::

        _=AuthControl("system.user.create")
        _=AuthControl("system.user.edit", "system.user.publish")
    """
    if not codes:
        raise ValueError("AuthControl 至少需要一个权限码")
    return Depends(Permission(*codes))


__all__ = [
    "DBSession",
    "PageDep",
    "CurrentUser",
    "AdminUser",
    "AuthControl",
]
