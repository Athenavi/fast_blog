"""MCP 工具的权限判定 —— 对齐项目的**三段权限码**体系。

**为什么必须改**（修复前的真实状态）：原实现用 ``ROLE_HIERARCHY``
（superuser 100 / admin 80 / editor 60 / author 40 / user 20）按 ``user.role`` 的
**等级分**判权。但项目的真实权限体系是 ``module_{域}:{模块}:{动作}`` 三段码
（205 个，见 ``core/permission/codes.py``）+ 数据范围，而且**一个用户可以有多个角色** ——
单个 ``role`` 字段根本无法表达「他是否拥有 ``module_ops:backup:create``」。
结论：判权与真实权限脱节，而且**上下文从未被注入**（全仓无人调用 ``set_user_ctx``），
所以 53 个工具实际上都执行不了。

现在：``UserCtx`` 携带真实权限码（``load_codes`` 的结果，API Token 场景再与 ``scopes`` 求交），
本模块按码判定，规则与 REST 的 ``AuthControl`` 保持一致：

  1. 超级管理员直接放行（与 REST 相同的唯一 bypass）；
  2. 请求侧或用户侧持有通配码（``*`` / ``*:*:*``）→ 放行；
  3. **ANY 语义**：任一所需权限码命中即通过（含过渡期旧码等价写法）；
  4. 任何异常一律 **fail-closed**（拒绝），绝不因信息缺失而放行。
"""

from __future__ import annotations

import logging
from typing import Callable, FrozenSet, Iterable, Optional

from src.api.v3.core.permission.codes import legacy_aliases_of
from src.api.v3.core.permission.constants import WILDCARD_CODES
from src.mcp._context import UserCtx, get_user_ctx

logger = logging.getLogger("mcp.perms")


def get_current_user() -> Optional[UserCtx]:
    """工具处理器获取当前用户身份（由各传输层注入 contextvar）"""
    return get_user_ctx()


# ────────────────────────────────────────────────────────── 工具 → 所需权限码
#
# 每个工具声明它对应的**真实权限码**（与同能力的 REST 端点保持一致）。
# 集中维护的意义：新增工具时若忘记声明，`ensure_tool_allowed` 会因查不到而**拒绝**
# （fail-closed），不会有"漏判即放行"的静默漏洞。
#
# 个别工具在权限码体系里没有对应域（项目无 workflow / collaboration 域码），
# 下面用注释标明了取近似码的理由，而不是编造一个不存在的码。

TOOL_PERMISSIONS: dict[str, tuple[str, ...]] = {
    # ── 文章 ──
    "create_article": ("module_content:article:create",),
    "update_article": ("module_content:article:edit",),
    "delete_article": ("module_content:article:delete",),
    "search_articles": ("module_content:article:view",),
    "batch_publish_articles": ("module_content:article:publish",),
    "get_trending_articles": ("module_analytics:dashboard:view",),
    # ── 分类 / 标签 ──
    "create_category": ("module_content:category:create",),
    "update_category": ("module_content:category:edit",),
    "delete_category": ("module_content:category:delete",),
    "list_categories": ("module_content:category:view",),
    "list_tags": ("module_content:tag:view",),
    # ── 媒体 ──
    "list_media": ("module_content:media:view",),
    "delete_media": ("module_content:media:delete",),
    # ── 评论 ──
    "list_comments": ("module_content:comment:view",),
    "approve_comment": ("module_content:comment:approve",),
    "reject_comment": ("module_content:comment:approve",),
    "delete_comment": ("module_content:comment:delete",),
    # ── 审批 ──
    "list_pending_reviews": ("module_content:approval:view",),
    "approve_content": ("module_content:approval:act",),
    "reject_content": ("module_content:approval:act",),
    # ── 协作（项目无 collaboration 域码 → 取文章查看权限：协作者列表属文章协作范围）──
    "list_collaborators": ("module_content:article:view",),
    # ── 用户 ──
    "create_user": ("module_system:user:create",),
    "ban_user": ("module_system:user:edit",),
    "update_user_role": ("module_system:user:manage_roles",),
    "list_users": ("module_system:user:view",),
    "get_user_stats": ("module_system:user:view",),
    "list_user_activity": ("module_system:user:view",),
    # ── 设置 / 系统 ──
    "get_settings": ("module_system:setting:view",),
    "update_settings": ("module_system:setting:edit",),
    "get_maintenance_mode": ("module_system:setting:view",),
    "set_maintenance_mode": ("module_system:setting:edit",),
    "get_system_info": ("module_system:monitor:view",),
    "get_system_stats": ("module_system:monitor:view",),
    "get_performance_metrics": ("module_system:monitor:view",),
    "get_workflow_stats": ("module_system:monitor:view",),
    "list_rate_limits": ("module_system:monitor:manage",),
    # ── 安全 / 审计 ──
    "get_security_report": ("module_system:security:view",),
    "query_audit_log": ("module_system:security:view",),
    "export_audit_log": ("module_ops:audit:export",),
    "manage_sensitive_word": ("module_system:sensitive_word:edit",),
    "scan_sensitive_words": ("module_system:sensitive_word:view",),
    # ── 缓存 ──
    "clear_cache": ("module_system:cache:clear",),
    "get_cache_status": ("module_system:cache:view",),
    # ── 运维 ──
    "create_backup": ("module_ops:backup:create",),
    "list_backups": ("module_ops:backup:view",),
    "run_migration": ("module_ops:migration:create",),
    "send_test_email": ("module_ops:email:edit",),
    # ── 通知 / Webhook ──
    "list_webhooks": ("module_ops:webhook:view",),
    "list_notifications": ("module_ops:notification:view",),
    "mark_notification_read": ("module_ops:notification:edit",),
    "send_bulk_notification": ("module_ops:notification:edit",),
    # ── 分析 / SEO ──
    "get_analytics": ("module_analytics:dashboard:view",),
    "generate_seo_description": ("module_analytics:seo:edit",),
}


def _satisfied(required: str, owned: FrozenSet[str]) -> bool:
    """所需权限码是否被满足（与 ``core/permission/control.py`` 同逻辑，含过渡期旧码兼容）"""
    if required in owned:
        return True
    return bool(legacy_aliases_of(required) & owned)


def has_permission(*codes: str, user: Optional[UserCtx] = None) -> bool:
    """是否满足所需的任一权限码（ANY 语义）。无用户上下文 → False（fail-closed）"""
    ctx = user or get_current_user()
    if ctx is None:
        return False
    if ctx.is_superuser:
        return True
    if not codes:
        return True  # 未声明权限码 ⇒ 仅需登录（与 REST 一致）

    owned = ctx.effective_codes()
    if WILDCARD_CODES.intersection(owned):
        return True
    return any(_satisfied(code, owned) for code in codes)


def require_self_or_admin(user_id_key: str = "user_id", *, permission: str = "") -> Callable:
    """允许「本人」或「拥有指定权限的人」。

    原实现用 ``user.role in ("admin", "superuser")`` 判「管理员」—— 角色名判定，与真实权限体系
    脱节（有 admin 角色不等于拥有某个具体权限码）。改为：超管 或 持有 ``permission`` 权限码
    视为管理员；否则只允许操作 ``user_id_key`` 指向自己的数据。
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(arguments: dict) -> dict:
            ctx = get_current_user()
            if ctx is None:
                return {"success": False, "error": "未登录", "code": "UNAUTHORIZED"}
            if ctx.is_superuser or (permission and has_permission(permission, user=ctx)):
                return await func(arguments)
            target_id = arguments.get(user_id_key)
            if target_id is not None:
                try:
                    if int(target_id) == ctx.id:
                        return await func(arguments)
                except (TypeError, ValueError):
                    pass
            return {"success": False, "error": "只能操作自己的数据", "code": "FORBIDDEN"}

        return wrapper

    return decorator


def require_permission(*codes: str) -> Callable:
    """要求用户拥有给定权限码之一（ANY 语义）。

    用法：``@require_permission("module_content:article:edit")``
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(arguments: dict) -> dict:
            ctx = get_current_user()
            if ctx is None:
                return {
                    "success": False,
                    "error": "未登录，无法执行操作",
                    "code": "UNAUTHORIZED",
                }
            if not has_permission(*codes, user=ctx):
                logger.warning(
                    "MCP 权限不足 user=%s 需要=%s 已拥有=%d 项",
                    ctx.username,
                    codes,
                    len(ctx.effective_codes()),
                )
                return {
                    "success": False,
                    "error": f"权限不足：需要 {' 或 '.join(codes)}",
                    "code": "FORBIDDEN",
                }
            return await func(arguments)

        return wrapper

    return decorator


def require_superuser(func: Callable) -> Callable:
    """要求超级管理员（保留原语义：判定的是 ``is_superuser``，不是角色名）"""

    async def wrapper(arguments: dict) -> dict:
        ctx = get_current_user()
        if ctx is None:
            return {"success": False, "error": "未登录", "code": "UNAUTHORIZED"}
        if not ctx.is_superuser:
            return {"success": False, "error": "需要超级管理员权限", "code": "FORBIDDEN"}
        return await func(arguments)

    return wrapper


def required_codes_for(tool_name: str) -> Optional[tuple[str, ...]]:
    """该工具声明的权限码；未声明返回 ``None``（调用方应据此拒绝，而不是放行）"""
    return TOOL_PERMISSIONS.get(tool_name)


def ensure_tool_allowed(tool_name: str) -> Optional[dict]:
    """工具调用的**统一防线**（由 ``MCPServer._handle_tool_call`` 调用）。

    返回 ``None`` 表示放行；否则返回应直接回给客户端的错误体。
    未在映射表里声明的工具一律**拒绝**（fail-closed），避免新增工具忘记声明即被放行。
    """
    ctx = get_current_user()
    if ctx is None:
        return {
            "success": False,
            "error": "未登录，无法执行操作",
            "code": "UNAUTHORIZED",
        }

    codes = required_codes_for(tool_name)
    if codes is None:
        logger.error("工具 %s 未在 TOOL_PERMISSIONS 中声明权限码，已按 fail-closed 拒绝", tool_name)
        return {
            "success": False,
            "error": f"工具 {tool_name} 未声明所需权限，已拒绝执行（服务端配置缺失）",
            "code": "FORBIDDEN",
        }

    if not has_permission(*codes, user=ctx):
        logger.warning("MCP 工具被拒 tool=%s user=%s 需要=%s", tool_name, ctx.username, codes)
        return {
            "success": False,
            "error": f"权限不足：需要 {' 或 '.join(codes)}",
            "code": "FORBIDDEN",
        }
    return None


def describe_tool_permissions(tools: Iterable[str]) -> dict:
    """给 ``tools/list`` 用：把所需权限码一并暴露，便于客户端预先判断而非撞 403"""
    return {name: list(TOOL_PERMISSIONS.get(name, ())) for name in tools}


__all__ = [
    "TOOL_PERMISSIONS",
    "describe_tool_permissions",
    "ensure_tool_allowed",
    "get_current_user",
    "has_permission",
    "require_permission",
    "require_self_or_admin",
    "require_superuser",
    "required_codes_for",
]
