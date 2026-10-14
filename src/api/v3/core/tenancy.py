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


__all__ = [
    "GLOBAL_TABLES",
    "apply_site_scope",
    "get_current_site_id",
    "is_site_scope_bypassed",
    "is_site_scoped_model",
    "reset_current_site",
    "set_current_site",
    "set_site_bypass",
    "site_filter_value",
]
