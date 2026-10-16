"""多租户站点上下文（唯一权威实现）

## 为什么用 ContextVar 而不是 ``request.state``

隔离必须落在 **CRUD / service 层**，那里拿不到 ``Request``。``ContextVar`` 在
asyncio 里天然按任务隔离：中间件在调用下游**之前**写入，请求结束即重置；
没有请求上下文的后台任务 / CLI 保持默认值 ``None``，于是**不做站点过滤**
（否则定时任务、迁移脚本会看不到任何数据）。

⚠️ 写入时机很关键：``BaseHTTPMiddleware`` 把下游 app 跑在**新 task** 里，
而 ``asyncio`` 创建 task 时复制当前 context。因此**必须**在 ``await call_next()``
之前调用 :func:`set_current_site`，否则下游读不到。

## 什么情况下才过滤

1. 模型有 ``site_id`` 列 ——  没有就跳过（便于按表分批纳入，不阻塞迁移）；
2. 上下文里有站点 ID ——  否则视为"全局视角"（后台任务 / CLI）；
3. 没有显式跨站点开关 ——  见 :func:`set_current_site` 的 ``bypass``。

## 跨站点（bypass）只能由服务端开启

``bypass`` 代表"看到所有站点的数据"，属于特权。它**只应由鉴权层**在确认
调用者是超级管理员、且请求显式声明要跨站点时写入（见 ``core/deps.py``），
绝不能由客户端头直接决定。
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Optional, Tuple

#: 当前请求所属站点 ID；None = 无站点上下文（不过滤）
_current_site_id: ContextVar[Optional[int]] = ContextVar("fastblog_current_site_id", default=None)

#: 是否显式跨站点（超级管理员专用开关）
_bypass_site_scope: ContextVar[bool] = ContextVar("fastblog_bypass_site_scope", default=False)

#: 始终不参与站点过滤的表（全局配置/站点自身等）
GLOBAL_TABLES = frozenset(
    {
        "sites",
        "site_users",
        "content_mappings",
        "system_settings",
        "alembic_version",
        # 审计与安全事件是**跨站点**的治理数据，按站点过滤会让超管看不见全貌
        "audit_logs",
        "login_attempts",
        "token_blacklist",
    }
)


def set_current_site(
    site_id: Optional[int], *, bypass: bool = False
) -> Tuple[Token, Token]:
    """写入站点上下文；返回两个 token，调用方必须在 ``finally`` 里 :func:`reset_current_site`"""
    return (_current_site_id.set(site_id), _bypass_site_scope.set(bypass))


def reset_current_site(tokens: Tuple[Token, Token]) -> None:
    """还原站点上下文（务必放在 ``finally`` 中，避免污染复用同一 context 的后续任务）"""
    site_token, bypass_token = tokens
    _current_site_id.reset(site_token)
    _bypass_site_scope.reset(bypass_token)


def set_site_bypass(value: bool) -> Token:
    """开启/关闭跨站点视图

    ⚠️ 这是"看到所有站点数据"的开关，**只能由鉴权层**在确认调用者是超级管理员、
    且请求显式声明要跨站点时调用（见 ``src/auth/auth_deps.py``）。
    绝不要让它由客户端请求头直接决定 —— 那等于把隔离关了。
    """
    return _bypass_site_scope.set(value)


def get_current_site_id() -> Optional[int]:
    return _current_site_id.get()


def is_site_scope_bypassed() -> bool:
    return _bypass_site_scope.get()


def is_site_scoped_model(model: Any) -> bool:
    """模型是否参与站点隔离（有 ``site_id`` 列且不在全局表清单里）"""
    table = getattr(model, "__tablename__", None)
    if not table or table in GLOBAL_TABLES:
        return False
    columns = getattr(getattr(model, "__table__", None), "columns", None)
    if columns is None:
        return False
    return "site_id" in {column.key for column in columns}


def site_filter_value(model: Any) -> Optional[int]:
    """返回应当用哪个 site_id 过滤；``None`` 表示不注入条件

    三种情况返回 ``None``：模型不参与隔离、没有站点上下文、或已显式跨站点。
    """
    if is_site_scoped_model(model) is False:
        return None
    if is_site_scope_bypassed():
        return None
    return get_current_site_id()


def apply_site_scope(stmt: Any, model: Any) -> Any:
    """给**手写查询**注入站点过滤；返回新的语句

    ⚠️ 这是隔离的补充入口。``CRUDBase`` 的 ``_build_query`` / ``get`` / ``count`` /
    ``bulk_remove`` 已经自动注入，但各模块里手写的 ``select(Article)`` 不经过那里 ——
    实测有 27 处（``article.service._published_stmt``、``analytics/seo/sitemap``、
    ``content/feed``、``content/recommend``、``content/tag``、``content/comment`` 等）。

    漏加的后果不是"少了个过滤"，而是**前后不一致**：列表能跨站点看到标题，
    点进详情（走 ``crud.get``）却被拦成 404 —— 既是信息泄漏，也是可观测的怪异行为。

    ``site_filter_value`` 返回 ``None`` 时原样返回语句（后台任务 / CLI / 已跨站点）。
    """
    site_id = site_filter_value(model)
    if site_id is None:
        return stmt
    return stmt.where(getattr(model, "site_id") == site_id)


def apply_site_scope_to_statement(statement: Any) -> Any:
    """给 ORM SELECT 语句注入站点条件（不做上下文判定，供事件层与单测复用）

    用 ``with_loader_criteria`` 而不是 ``.where()``：后者只作用于主查询，
    而前者会**传播到 relationship 的懒加载**（``include_aliases=True`` 还覆盖别名），
    否则 ``article.category`` 这类关联对象仍会跨站点取到。

    **已知局限**：判定依据是语句的 ``column_descriptions`` 里出现了哪些实体，因此
    ``select(func.count()).select_from(stmt.subquery())`` 这类"外层全是聚合函数"的语句
    不会被改写 —— 若其内层子查询来自未过滤的手写 select，计数会偏大。
    影响仅限**统计数字**，不会泄漏行内容（行的拦截发生在 ``select(Model)`` 主查询上）。
    需要精确计数时，用 :func:`apply_site_scope` 显式包一层内层查询。
    """
    from sqlalchemy.orm import with_loader_criteria

    site_id = get_current_site_id()
    if site_id is None or is_site_scope_bypassed():
        return statement

    try:
        descriptions = statement.column_descriptions
    except Exception:  # noqa: BLE001 - 拿不到描述就不介入
        return statement

    entities = {
        item.get("entity")
        for item in descriptions
        if item.get("entity") is not None and is_site_scoped_model(item.get("entity"))
    }
    for entity in entities:
        statement = statement.options(
            with_loader_criteria(
                entity,
                getattr(entity, "site_id") == site_id,
                include_aliases=True,
            )
        )
    return statement


_ORM_SCOPE_INSTALLED = False


def install_orm_site_scope() -> bool:
    """装上 ORM 级的租户隔离兜底；返回是否为本次首装

    为什么需要：``CRUDBase`` 的过滤只覆盖走基类的查询，而各模块里手写的
    ``select(Article)`` / ``select(Comment)`` 等不经过那里（实测 27 处，且只能是
    "当时扫到的"）。逐个补既容易漏，也约束不了后续新写的代码。

    这里通过 SQLAlchemy 的 ``do_orm_execute`` 事件在**语句执行前**统一注入，覆盖
    所有 ORM SELECT（含 relationship 懒加载）。

    生效条件与 :func:`site_filter_value` 保持一致：有站点上下文、未显式跨站点、
    目标实体带 ``site_id`` 列且不在 ``GLOBAL_TABLES``。**没有站点上下文时完全不介入**
    （后台任务 / CLI / 迁移脚本因此照常工作）。
    """
    global _ORM_SCOPE_INSTALLED
    if _ORM_SCOPE_INSTALLED:
        return False

    from sqlalchemy import event
    from sqlalchemy.orm import Session

    @event.listens_for(Session, "do_orm_execute")
    def _apply_tenant_scope(execute_state) -> None:  # noqa: ANN001
        try:
            if not execute_state.is_select or execute_state.is_column_load:
                return
            execute_state.statement = apply_site_scope_to_statement(execute_state.statement)
        except Exception:  # noqa: BLE001 - 隔离层自身出错不能拖垮查询
            return

    _ORM_SCOPE_INSTALLED = True
    return True


__all__ = [
    "GLOBAL_TABLES",
    "apply_site_scope",
    "apply_site_scope_to_statement",
    "get_current_site_id",
    "install_orm_site_scope",
    "is_site_scope_bypassed",
    "is_site_scoped_model",
    "reset_current_site",
    "set_current_site",
    "set_site_bypass",
    "site_filter_value",
]
