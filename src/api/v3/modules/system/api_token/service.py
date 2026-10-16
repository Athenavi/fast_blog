"""api_token 模块业务逻辑：签发 / 列出 / 撤销对外 API 令牌。

关键约束（安全）：

  1. **越权不可签发**：``scopes`` 必须是归属用户当前权限码的子集，否则 400。
     （用户持通配码时视为不受限。）
  2. **明文只出现一次**：库里只有 Argon2 哈希与前缀；创建响应之后无法再取回。
  3. **可见性**：普通用户只能看到/撤销**自己**的令牌；管理员（superuser）可见全部。
     撤销采用软删（``is_active=False``），保留审计线索。
"""

from datetime import datetime, timedelta
from typing import Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import ApiToken
from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.core.permission.constants import WILDCARD_CODES
from src.api.v3.core.permission.loader import load_codes
from src.auth.api_token import generate_token, scopes_from_text, scopes_to_text


def _to_out(row: ApiToken, *, include_user: bool = False) -> dict:
    data = {
        "id": row.id,
        "name": row.name,
        "token_prefix": row.token_prefix,
        "scopes": sorted(scopes_from_text(row.scopes)),
        "expires_at": row.expires_at,
        "last_used_at": row.last_used_at,
        "is_active": bool(row.is_active),
        "created_at": row.created_at,
    }
    if include_user:
        data["user_id"] = row.user_id
    return data


class ApiTokenService:
    """对外 API 令牌（system 域）"""

    @staticmethod
    def _is_admin(user: Any) -> bool:
        return bool(getattr(user, "is_superuser", False))

    async def list_tokens(self, db: AsyncSession, *, user: Any) -> tuple[list[dict], bool]:
        """返回 ``(令牌列表, 是否管理员视角)``；普通用户仅自己。"""
        is_admin = self._is_admin(user)
        stmt = select(ApiToken).order_by(ApiToken.id.desc())
        if not is_admin:
            stmt = stmt.where(ApiToken.user_id == user.id)
        rows = (await db.execute(stmt)).scalars().all()
        return [_to_out(row, include_user=is_admin) for row in rows], is_admin

    async def create_token(
        self,
        db: AsyncSession,
        *,
        user: Any,
        name: str,
        scopes: List[str],
        expires_in_days: int,
    ) -> dict:
        """签发令牌，返回**含明文**的输出（仅此一次）。"""
        requested = {str(code).strip() for code in scopes if str(code).strip()}
        if not requested:
            raise BadRequestError("scopes 不能为空：请显式声明该令牌允许的权限码")

        owned = frozenset(await load_codes(db, user.id))
        if not WILDCARD_CODES.intersection(owned):
            overflow = sorted(requested - owned)
            if overflow:
                raise ForbiddenError(
                    "令牌权限不能超出发起者自身权限，以下权限码未持有：" + ", ".join(overflow)
                )

        plaintext, prefix, token_hash = generate_token()
        now = datetime.now()
        row = ApiToken(
            name=name,
            token_prefix=prefix,
            token_hash=token_hash,
            scopes=scopes_to_text(requested),
            user_id=getattr(user, "id", None),
            expires_at=now + timedelta(days=expires_in_days),
            last_used_at=None,
            is_active=True,
            created_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        data = _to_out(row, include_user=True)
        data["token"] = plaintext  # 明文仅此一次
        return data

    async def revoke_token(self, db: AsyncSession, *, user: Any, token_id: int) -> None:
        """撤销（软删）；非本人且非管理员 → 404（不泄露"存在但不属于你"）。"""
        row = (
            await db.execute(select(ApiToken).where(ApiToken.id == token_id))
        ).scalars().first()
        if row is None:
            raise NotFoundError("令牌不存在")
        if not self._is_admin(user) and row.user_id != getattr(user, "id", None):
            raise NotFoundError("令牌不存在")

        if row.is_active:
            row.is_active = False
            await db.commit()
