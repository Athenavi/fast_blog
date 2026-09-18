"""权限控制依赖（对齐 FastApiAdmin 的 `AuthPermission`）

语义（与官方一致）：

  - **superuser 直接放行**（整个后端只保留这一处 bypass）
  - 未声明权限码 ⇒ 仅需认证
  - 通配 `*` / `*:*:*` ⇒ 放行（请求侧或用户侧任一持有即视为不受限）
  - **ANY 语义**：任一权限码命中即通过（官方实现是 `any(perm in user_permissions ...)`）
  - 任何异常一律 **fail-closed**（403），绝不因缓存/DB 故障而放行

与旧实现的差异（有意的行为变更）：

  旧的 `_permission.Permission` 是 **AND** 语义。经核查 v3 现有 152 处 `AuthControl`
  用法**全部只传一个权限码**，因此切换为 ANY 不影响任何现有端点，且与官方对齐。

P4 迁移到官方三段式（``module_{域}:{模块}:{动作}``）后，此处增加**过渡期兼容**：
``codes.LEGACY_ALIASES`` 里的"纯改名"权限码，其旧写法仍被接受（P6 移除）。
"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User as UserModel
from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.codes import legacy_aliases_of
from src.api.v3.core.permission.constants import WILDCARD_CODES, normalize_code
from src.api.v3.core.permission.loader import load_codes
from src.auth.auth_deps import get_current_user
from src.utils.database.unified_manager import get_db_session

logger = get_logger("permission.control")

#: 是否启用过渡期旧码兼容（P6 关闭并删除 LEGACY_ALIASES）
LEGACY_COMPAT_ENABLED = True


def _satisfied(required: str, owned: set[str] | frozenset[str]) -> bool:
    """要求的权限码是否被满足（过渡期同时接受其旧的等价写法）"""
    if required in owned:
        return True
    if not LEGACY_COMPAT_ENABLED:
        return False
    return bool(legacy_aliases_of(required) & owned)


class AuthPermission:
    """权限校验依赖：ANY + 通配 + 单点 superuser bypass + fail-closed"""

    __slots__ = ("permissions",)

    def __init__(self, *permissions: str) -> None:
        self.permissions = tuple(normalize_code(code) for code in permissions)

    async def __call__(
        self,
        request: Request,
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> UserModel:
        # 1. superuser 放行
        if getattr(user, "is_superuser", False):
            return user

        # 2. 未声明权限码 ⇒ 仅需认证
        if not self.permissions:
            return user

        # 3. 请求侧要求通配 ⇒ 不限制
        if WILDCARD_CODES.intersection(self.permissions):
            return user

        # 4. 读取用户权限集合（失败即拒绝，不放行）
        try:
            owned = await load_codes(db, user.id, request=request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("权限码加载失败 user=%s", getattr(user, "id", None))
            raise ForbiddenError("权限校验失败") from exc

        # 5. 用户持有通配 ⇒ 放行
        if WILDCARD_CODES.intersection(owned):
            return user

        # 6. ANY 语义（过渡期同时接受旧的两段写法）
        if not any(_satisfied(code, owned) for code in self.permissions):
            logger.warning(
                "权限不足 user=%s 需要=%s 已拥有=%d 项",
                getattr(user, "id", None),
                self.permissions,
                len(owned),
            )
            raise ForbiddenError(f"权限不足：需要 {', '.join(self.permissions)}")

        return user


def AuthControl(*permissions: str):
    """权限依赖工厂（保持既有调用签名：``_perm=AuthControl(codes.ARTICLE_VIEW)``）"""
    if not permissions:
        raise ValueError("AuthControl 至少需要一个权限码")
    return Depends(AuthPermission(*permissions))


__all__ = ["AuthPermission", "AuthControl"]
