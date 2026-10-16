"""shortcode 模块业务逻辑：短代码库（[code] -> 预定义内容片段）

code 唯一；创建后锁定（更新 schema 不含 code，语义对齐 custom_post_type 的 slug）。
"""

import re
from datetime import datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.content.shortcode import Shortcode
from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.content.shortcode.crud import shortcode_crud
from src.api.v3.modules.content.shortcode.schema import (
    ShortcodeCreate,
    ShortcodeOut,
    ShortcodeUpdate,
)

#: 短代码语法 ``[code]``；code 的字符集与 schema 的 pattern 保持一致
_SHORTCODE_PATTERN = re.compile(r"\[([a-z0-9_-]+)\]")


def _to_out(row) -> dict:
    return ShortcodeOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class ShortcodeService:
    """短代码库（content 域）"""

    async def list_shortcodes(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await shortcode_crud.list(
            db, page=page, page_size=page_size, keyword=keyword,
            filters={"is_active": is_active},
        )
        return [_to_out(r) for r in rows], total

    async def create_shortcode(self, db: AsyncSession, payload: ShortcodeCreate) -> dict:
        if await shortcode_crud.exists(db, code=payload.code):
            raise ConflictError(f"短代码标识已存在: {payload.code}")
        row = await shortcode_crud.create(
            db, payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()}
        )
        return _to_out(row)

    async def update_shortcode(
        self, db: AsyncSession, shortcode_id: int, payload: ShortcodeUpdate
    ) -> dict:
        row = await shortcode_crud.get(db, shortcode_id)
        if row is None:
            raise NotFoundError("短代码不存在")
        updated = await shortcode_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _to_out(updated)

    async def delete_shortcode(self, db: AsyncSession, shortcode_id: int) -> None:
        row = await shortcode_crud.get(db, shortcode_id)
        if row is None:
            raise NotFoundError("短代码不存在")
        await shortcode_crud.remove(db, row)

    # ------------------------------------------------------------------ 渲染期展开

    async def expand_for_content(
        self, db: AsyncSession, content: Optional[str], *, site_id: Optional[int] = None
    ) -> Optional[str]:
        """把正文里的 ``[code]`` 展开成 ``shortcodes`` 表里对应条目的 ``content``。

        在此之前这个模块**只有 CRUD、没有任何展开逻辑**（全仓搜不到
        ``apply_shortcode``/``render_shortcode``/``replace_shortcode``），
        也就是短代码存进库里对正文毫无影响 —— 这里补上渲染期的展开。

        四条必须守住的行为：

        1. **只替换启用中的短代码**，未登记或已停用的 ``code`` **原样保留**。
           正文里出现方括号是常事（引用、代码片段），不能因为查不到就把它删掉。
        2. **不递归展开**。替换进来的内容里若再出现 ``[code]`` 不再处理，
           否则两个互相引用的短代码会无限展开。
        3. **多租户**：优先用当前 ``site_id`` 的条目；``site_id`` 为空的
           （全局短代码）作为回落。传入 ``None`` 时只匹配全局条目。
        4. **一次查询**：先正则取出全部候选 code，再一条 ``IN`` 查询，
           避免正文里有几十个短代码时逐个查库。
        """
        if not content:
            return content

        codes = {m.group(1) for m in _SHORTCODE_PATTERN.finditer(content)}
        if not codes:
            return content

        stmt = select(Shortcode).where(
            Shortcode.is_active.is_(True),
            Shortcode.code.in_(sorted(codes)),
        )
        if site_id is not None:
            stmt = stmt.where(
                or_(Shortcode.site_id == site_id, Shortcode.site_id.is_(None))
            )
        else:
            stmt = stmt.where(Shortcode.site_id.is_(None))

        rows = (await db.execute(stmt)).scalars().all()

        # 站点专属优先于全局：先放全局再让专属覆盖
        mapping: dict[str, str] = {}
        for row in rows:
            if row.site_id is None:
                mapping.setdefault(row.code, row.content or "")
            else:
                mapping[row.code] = row.content or ""

        if not mapping:
            return content

        def _replace(match: re.Match) -> str:
            # 查不到的 code 原样返回（见行为 1）
            return mapping.get(match.group(1), match.group(0))

        return _SHORTCODE_PATTERN.sub(_replace, content)


shortcode_service = ShortcodeService()
