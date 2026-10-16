"""权限码加载（三层缓存 + 角色继承）

改进点（相对历史实现）：

  1. **角色继承用 PostgreSQL 递归 CTE**，替代"Python 端 BFS + 硬编码深度 5" ——
     层级更深时不再被静默截断。
  2. 加载结果是 `frozenset`（不可变），避免被调用方意外改写缓存内容。
  3. 查询只取"激活的能力 + 激活的角色"，与 `seed_rbac.py` 的数据形态一致。
"""

from typing import Any, FrozenSet, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.cache import (
    get_request_codes,
    memory_cache,
    redis_get_codes,
    redis_set_codes,
    set_request_codes,
)

logger = get_logger("permission.loader")

#: 角色继承 + 能力码收集（一条 SQL 完成，含 parent_id 向上继承）
_LOAD_CODES_SQL = text(
    """
    WITH RECURSIVE role_tree AS (
        SELECT r.id, r.parent_id
          FROM roles r
          JOIN user_role_assignments ur ON ur.role_id = r.id
         WHERE ur.user_id = :user_id
           AND r.is_active IS TRUE
        UNION
        SELECT parent.id, parent.parent_id
          FROM roles parent
          JOIN role_tree child ON parent.id = child.parent_id
         WHERE parent.is_active IS TRUE
    )
    SELECT DISTINCT c.code
      FROM capabilities c
      JOIN role_capabilities rc ON rc.capability_id = c.id
     WHERE rc.role_id IN (SELECT id FROM role_tree)
       AND c.is_active IS TRUE
    """
)


async def load_codes_from_db(db: AsyncSession, user_id: int) -> FrozenSet[str]:
    """直接从数据库加载用户权限码（含角色继承）"""
    try:
        rows = (await db.execute(_LOAD_CODES_SQL, {"user_id": user_id})).scalars().all()
    except Exception:  # noqa: BLE001 - 递归 CTE 在极端方言下可能不可用，回退到扁平查询
        logger.exception("递归 CTE 加载权限码失败，回退到扁平查询 user=%s", user_id)
        rows = (
            await db.execute(
                text(
                    """
                    SELECT DISTINCT c.code
                      FROM capabilities c
                      JOIN role_capabilities rc ON rc.capability_id = c.id
                      JOIN user_role_assignments ur ON ur.role_id = rc.role_id
                     WHERE ur.user_id = :user_id AND c.is_active IS TRUE
                    """
                ),
                {"user_id": user_id},
            )
        ).scalars().all()

    return frozenset(str(code) for code in rows if code)


async def load_codes(
    db: AsyncSession,
    user_id: int,
    *,
    request: Optional[Any] = None,
) -> FrozenSet[str]:
    """按 request.state → 内存 → Redis → DB 的顺序读取权限码，并回填各级缓存"""
    if request is not None:
        cached = get_request_codes(request)
        if cached is not None:
            return cached

    cached = await memory_cache.get(user_id)
    if cached is not None:
        if request is not None:
            set_request_codes(request, cached)
        return cached

    cached = await redis_get_codes(user_id)
    if cached is not None:
        await memory_cache.set(user_id, cached)
        if request is not None:
            set_request_codes(request, cached)
        return cached

    codes = await load_codes_from_db(db, user_id)
    # 注意：空集合也会回填。用户确实没有权限时反复查库没有意义，
    # 而权限变更后由 invalidate 主动清理，不存在"长期脏缓存"。
    await memory_cache.set(user_id, codes)
    await redis_set_codes(user_id, codes)
    if request is not None:
        set_request_codes(request, codes)
    return codes


__all__ = ["load_codes", "load_codes_from_db"]
