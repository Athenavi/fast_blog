"""数据范围过滤（唯一实现）

对应方案 §7.7.5：**采纳官方的"按创建人推导"**（业务表只记归属人，不为数据行加 group_id），
并强制补齐官方缺失的四项：

  ① **可访问组集合缓存**（Redis + 变更失效）—— 官方每次查库、每次全表拉部门算子树
  ② **子查询而非展开 id 列表** —— 避免成员规模放大 IN 列表
  ③ **无归属数据策略显式化** —— ``owner IS NULL``（或作者已被删除）默认**不可见**，
     只有 ``data_scope=全部`` 的用户可见；不再依赖"猜"
  ④ **``DATA_SCOPED_MODELS`` 显式登记** —— 未登记的模型明确不做数据级过滤，
     而不是像官方那样靠 ``hasattr(model, 'created_id')`` 静默 no-op

另有两个与官方一致的正确取舍：

  - 多角色取**并集**，且任一角色的档位为"全部"即不过滤（宽松优先）
  - 解析失败时**降级为最小授权（仅本人）**并留日志，绝不静默放宽

``data_scope`` 为 ``NULL``（模型侧可空，见方案 §8.2）时按 **1（仅本人）** 处理。
"""

from typing import Any, Optional, Set

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.cache import native_client
from src.api.v3.core.permission.constants import (
    DATA_SCOPE_ALL,
    DATA_SCOPE_CUSTOM,
    DATA_SCOPE_GROUP_AND_CHILD,
    DATA_SCOPE_SELF,
)

logger = get_logger("permission.scope")

#: 组集合缓存（用户 → 其"组及子组"id 集合）
SCOPE_GROUP_CACHE_PREFIX = "rbac:scope:groups:"
#: 自定义组缓存（用户 → 由角色 role_groups 指定的组 id 集合）
SCOPE_CUSTOM_CACHE_PREFIX = "rbac:scope:custom:"
SCOPE_CACHE_TTL = 300

#: 参与数据范围过滤的模型 → 归属字段名（**显式登记**；不在表内即不做数据级过滤）
_data_scoped_models: dict[Any, str] = {}


def register_data_scoped_models() -> dict[Any, str]:
    """填充并返回登记表（延迟导入模型，避免与 ``shared.models`` 形成导入环）"""
    global _data_scoped_models
    if _data_scoped_models:
        return _data_scoped_models

    from shared.models.article.article import Article
    from shared.models.comment.comment import Comment
    from shared.models.media.media import Media
    from shared.models.page.pages import Pages

    _data_scoped_models = {
        Article: "user",
        Comment: "user_id",
        Media: "user",
        Pages: "author_id",
    }
    return _data_scoped_models


def owner_field_of(model: Any) -> Optional[str]:
    """取模型的归属字段名；未登记返回 None（明确表示"该模型不做数据级过滤"）"""
    return register_data_scoped_models().get(model)


# ------------------------------------------------------------------ 缓存读写
async def _cache_get(key: str) -> Optional[Set[int]]:
    client = native_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取数据范围缓存失败 key=%s：%s", key, exc)
        return None
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, set)):
        values = raw
    else:
        values = str(raw).split(",")
    result = set()
    for item in values:
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            continue
    return result


async def _cache_set(key: str, values: Set[int]) -> None:
    client = native_client()
    if client is None:
        return
    try:
        await client.set(key, ",".join(str(v) for v in sorted(values)), ex=SCOPE_CACHE_TTL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("写入数据范围缓存失败 key=%s：%s", key, exc)


# ------------------------------------------------------------------ 组集合解析
_GROUP_TREE_SQL = """
                  WITH RECURSIVE my_groups AS (SELECT g.id, g.parent_id
                                               FROM permission_groups g
                                                        JOIN user_group_members m ON m.group_id = g.id
                                               WHERE m.user_id = :user_id
                                                 AND g.is_active IS TRUE
                                               UNION
                                               SELECT child.id, child.parent_id
                                               FROM permission_groups child
                                                        JOIN my_groups parent ON child.parent_id = parent.id
                                               WHERE child.is_active IS TRUE)
                  SELECT id
                  FROM my_groups \
                  """

_CUSTOM_GROUPS_SQL = """
                     SELECT DISTINCT rg.group_id
                     FROM role_groups rg
                              JOIN user_role_assignments ur ON ur.role_id = rg.role_id
                              JOIN roles r ON r.id = rg.role_id
                     WHERE ur.user_id = :user_id
                       AND r.is_active IS TRUE \
                     """


async def resolve_scope_group_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """用户"本组及以下"的组 id 集合（带 Redis 缓存）"""
    key = f"{SCOPE_GROUP_CACHE_PREFIX}{user_id}"
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    from sqlalchemy import text

    rows = (await db.execute(text(_GROUP_TREE_SQL), {"user_id": user_id})).scalars().all()
    group_ids = {int(row) for row in rows if row is not None}
    await _cache_set(key, group_ids)
    return group_ids


async def resolve_custom_group_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """``data_scope=5`` 时由角色指定的组 id 集合（带 Redis 缓存）"""
    key = f"{SCOPE_CUSTOM_CACHE_PREFIX}{user_id}"
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    from sqlalchemy import text

    rows = (await db.execute(text(_CUSTOM_GROUPS_SQL), {"user_id": user_id})).scalars().all()
    group_ids = {int(row) for row in rows if row is not None}
    await _cache_set(key, group_ids)
    return group_ids


# ------------------------------------------------------------------ 档位解析
def _normalize_scopes(scopes: Set[Optional[int]]) -> Set[int]:
    """``NULL`` 视为 1（仅本人）；无任何档位时同样按 1 处理（最小授权）"""
    normalized = {int(scope) if scope is not None else DATA_SCOPE_SELF for scope in scopes}
    return normalized or {DATA_SCOPE_SELF}


async def resolve_data_scopes(db: AsyncSession, user_id: int) -> Set[int]:
    """用户所有（含继承的父角色）有效角色的 data_scope 集合"""
    from sqlalchemy import text

    sql = """
          WITH RECURSIVE role_tree AS (SELECT r.id, r.parent_id, r.data_scope
                                       FROM roles r
                                                JOIN user_role_assignments ur ON ur.role_id = r.id
                                       WHERE ur.user_id = :user_id
                                         AND r.is_active IS TRUE
                                       UNION
                                       SELECT parent.id, parent.parent_id, parent.data_scope
                                       FROM roles parent
                                                JOIN role_tree child ON parent.id = child.parent_id
                                       WHERE parent.is_active IS TRUE)
          SELECT DISTINCT data_scope
          FROM role_tree \
          """
    rows = (await db.execute(text(sql), {"user_id": user_id})).scalars().all()
    return _normalize_scopes(set(rows))


# ------------------------------------------------------------------ 查询过滤
async def apply_data_scope(stmt: Select, model: Any, *, db: AsyncSession, user: Any) -> Select:
    """按当前用户的数据范围，给查询追加过滤条件

    - 未登记的模型：**明确不追加**（调用方若要求数据范围，应在启动期审计里被发现）
    - 超级管理员与 ``data_scope=全部``：不追加条件
    - 解析异常：降级为"仅本人"并记录日志（最小授权）
    """
    owner_name = owner_field_of(model)
    if owner_name is None:
        logger.debug("模型 %s 未登记数据范围，跳过过滤", getattr(model, "__name__", model))
        return stmt

    if getattr(user, "is_superuser", False):
        return stmt

    owner_column = getattr(model, owner_name)
    try:
        scopes = await resolve_data_scopes(db, user.id)
        if DATA_SCOPE_ALL in scopes:
            return stmt

        conditions = []
        if DATA_SCOPE_SELF in scopes:
            conditions.append(owner_column == user.id)

        group_ids: Set[int] = set()
        if DATA_SCOPE_GROUP_AND_CHILD in scopes:
            group_ids |= await resolve_scope_group_ids(db, user.id)
        if DATA_SCOPE_CUSTOM in scopes:
            group_ids |= await resolve_custom_group_ids(db, user.id)

        if group_ids:
            from shared.models.rbac.user_group_member import UserGroupMember

            member_ids = select(UserGroupMember.user_id).where(
                UserGroupMember.group_id.in_(sorted(group_ids))
            )
            conditions.append(owner_column.in_(member_ids))

        if not conditions:
            # 档位不认识或组为空 → 最小授权
            conditions.append(owner_column == user.id)

        return stmt.where(or_(*conditions))
    except Exception:  # noqa: BLE001 - 失败必须收紧，绝不放宽
        logger.exception("数据范围解析失败，降级为仅本人 user=%s model=%s", user.id, model)
        return stmt.where(owner_column == user.id)


async def ensure_object_in_scope(db: AsyncSession, model: Any, obj: Any, *, user: Any) -> None:
    """校验**单条记录**是否在用户的数据范围内；不在则抛 ``ForbiddenError``

    与 ``apply_data_scope`` 共用同一套档位解析，堵住"列表已过滤、但详情可直接猜 id 访问"的缺口。
    无归属字段（``owner IS NULL``）的记录只有 ``data_scope=全部`` 可见。
    """
    from src.api.v3.core.exceptions import ForbiddenError

    owner_name = owner_field_of(model)
    if owner_name is None or obj is None:
        return
    if getattr(user, "is_superuser", False):
        return

    owner_id = getattr(obj, owner_name, None)
    own = owner_id is not None and int(owner_id) == int(user.id)

    try:
        scopes = await resolve_data_scopes(db, user.id)
        if DATA_SCOPE_ALL in scopes:
            return
        if own and DATA_SCOPE_SELF in scopes:
            return

        needs_group = DATA_SCOPE_GROUP_AND_CHILD in scopes or DATA_SCOPE_CUSTOM in scopes
        if needs_group and owner_id is not None:
            group_ids: Set[int] = set()
            if DATA_SCOPE_GROUP_AND_CHILD in scopes:
                group_ids |= await resolve_scope_group_ids(db, user.id)
            if DATA_SCOPE_CUSTOM in scopes:
                group_ids |= await resolve_custom_group_ids(db, user.id)
            if group_ids:
                from shared.models.rbac.user_group_member import UserGroupMember

                exists = await db.scalar(
                    select(UserGroupMember.id).where(
                        UserGroupMember.group_id.in_(sorted(group_ids)),
                        UserGroupMember.user_id == owner_id,
                    )
                )
                if exists is not None:
                    return
    except Exception:  # noqa: BLE001 - 失败必须收紧
        logger.exception("数据范围校验失败 user=%s model=%s", getattr(user, "id", None), model)
        if own:
            return
        raise ForbiddenError("数据范围校验失败") from None

    raise ForbiddenError("无权访问该数据")


async def invalidate_scope_cache(user_id: Optional[int] = None) -> None:
    """失效数据范围缓存（组/成员/角色变更后必须调用）

    ``user_id=None`` 时按前缀清理（组结构变更会影响多个用户）。
    """
    client = native_client()
    if client is None:
        # Redis 不可用时依赖 TTL（300s）自然过期
        return
    try:
        if user_id is not None:
            await client.delete(f"{SCOPE_GROUP_CACHE_PREFIX}{user_id}")
            await client.delete(f"{SCOPE_CUSTOM_CACHE_PREFIX}{user_id}")
            return

        # 组结构/成员变更：按前缀清理（规模可控：单实例权限组数量通常很小）
        for prefix in (SCOPE_GROUP_CACHE_PREFIX, SCOPE_CUSTOM_CACHE_PREFIX):
            keys = await client.keys(f"{prefix}*")
            if keys:
                await client.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("失效数据范围缓存失败：%s", exc)


__all__ = [
    "apply_data_scope",
    "ensure_object_in_scope",
    "invalidate_scope_cache",
    "owner_field_of",
    "register_data_scoped_models",
    "resolve_custom_group_ids",
    "resolve_data_scopes",
    "resolve_scope_group_ids",
]
