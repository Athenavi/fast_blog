"""
审计日志订阅者

通过 EventBus 观察者模式异步记录审计日志。
CRUD 模块只需 emit 事件，本订阅者自动采集并写入 audit_log 表。

用法：
  在 CRUD 模块中 emit 事件：
      await event_bus.emit("article.updated", {...payload...})

  本模块自动监听所有已注册事件类型。
"""

import logging
from typing import Any, Dict, Optional

from shared.services.plugins.event_bus import event_bus, EventBus
from shared.services.security.audit_log_service import (
    AuditLogAction,
    AuditLogLevel,
    audit_log_service,
)

logger = logging.getLogger(__name__)

# ── 事件 → 审计动作映射 ──────────────────────────
# 格式: event_name: (AuditLogAction, resource_type)

AUDIT_EVENT_MAP: Dict[str, tuple[AuditLogAction, str]] = {
    # 文章
    "article.published": (AuditLogAction.CREATE, "article"),
    "article.updated": (AuditLogAction.UPDATE, "article"),
    "article.deleted": (AuditLogAction.DELETE, "article"),
    # 评论
    "comment.created": (AuditLogAction.CREATE, "comment"),
    "comment.approved": (AuditLogAction.UPDATE, "comment"),
    "comment.rejected": (AuditLogAction.UPDATE, "comment"),
    "comment.deleted": (AuditLogAction.DELETE, "comment"),
    # 用户
    "user.registered": (AuditLogAction.CREATE, "user"),
    "user.updated": (AuditLogAction.UPDATE, "user"),
    "user.deleted": (AuditLogAction.DELETE, "user"),
    "user.profile_updated": (AuditLogAction.UPDATE, "user"),
    "user.blocked": (AuditLogAction.UPDATE, "user"),
    "user.unblocked": (AuditLogAction.UPDATE, "user"),
    "user.login": (AuditLogAction.LOGIN, "auth"),
    "user.logout": (AuditLogAction.LOGOUT, "auth"),
    "user.login_failed": (AuditLogAction.LOGIN, "auth"),
    # 分类
    "category.created": (AuditLogAction.CREATE, "category"),
    "category.updated": (AuditLogAction.UPDATE, "category"),
    "category.deleted": (AuditLogAction.DELETE, "category"),
    # 媒体
    "media.uploaded": (AuditLogAction.CREATE, "media"),
    "media.deleted": (AuditLogAction.DELETE, "media"),
    "media.updated": (AuditLogAction.UPDATE, "media"),
    # 设置
    "settings.updated": (AuditLogAction.UPDATE, "settings"),
    "settings.secret_changed": (AuditLogAction.SECURITY_EVENT, "settings"),
    # 安全
    "security.rate_limited": (AuditLogAction.SECURITY_EVENT, "security"),
    "security.permission_change": (AuditLogAction.PERMISSION_CHANGE, "rbac"),
    # VIP / 会员
    "vip.subscription.created": (AuditLogAction.CREATE, "vip_subscription"),
    "vip.subscription.cancelled": (AuditLogAction.UPDATE, "vip_subscription"),
    "vip.subscription.expired": (AuditLogAction.UPDATE, "vip_subscription"),
    "vip.subscription.renewed": (AuditLogAction.CREATE, "vip_subscription"),
}

# 需要记录 WARNING/ERROR 级别的事件
HIGH_SEVERITY_EVENTS = {
    "user.login_failed",
    "settings.secret_changed",
    "security.rate_limited",
    "security.permission_change",
    "user.deleted",
    "article.deleted",
}


def _extract_field(payload: Any, key: str, default: Any = None) -> Any:
    """从事件 payload 中提取字段（支持 dict 和 dataclass）"""
    if isinstance(payload, dict):
        return payload.get(key, default)
    return getattr(payload, key, default)


def _get_payload_str(payload: Any) -> Optional[str]:
    """获取 payload 的描述字符串"""
    if isinstance(payload, dict):
        # 优先取 message，否则取 description，否则 None
        return payload.get("message") or payload.get("description")
    return getattr(payload, "message", None) or getattr(payload, "description", None)


async def _audit_log_handler(event_name: str, payload: Any) -> None:
    """通用审计日志处理函数"""
    mapping = AUDIT_EVENT_MAP.get(event_name)
    if not mapping:
        return

    action, resource_type = mapping

    # 提取公共字段
    user_id = _extract_field(payload, "user_id") or _extract_field(payload, "author_id")
    user_name = _extract_field(payload, "user_name") or _extract_field(payload, "username")
    raw_resource_id = _extract_field(payload, "id") or _extract_field(payload, "article_id")
    resource_id: Optional[str] = str(raw_resource_id) if raw_resource_id is not None else None
    description = _get_payload_str(payload) or f"{action.value} {resource_type}"

    level = AuditLogLevel.CRITICAL if event_name in HIGH_SEVERITY_EVENTS else AuditLogLevel.INFO

    # 异步记录审计日志（不阻塞调用方）
    try:
        from src.extensions import get_async_session_context

        async with get_async_session_context() as db:
            await audit_log_service.log_action(
                db=db,
                user_id=user_id,
                user_name=user_name,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                level=level,
            )
    except Exception as e:
        logger.error(f"[AuditLogSubscriber] Failed to log {event_name}: {e}")


def register_audit_subscriber(eb: Optional[EventBus] = None) -> None:
    """注册审计日志订阅者到 EventBus"""
    bus = eb or event_bus

    for event_name in AUDIT_EVENT_MAP:
        # 创建一个闭包，捕获 event_name
        async def _handler(payload: Any, _name: str = event_name) -> None:
            await _audit_log_handler(_name, payload)

        bus.listen(event_name, _handler)

    logger.info(
        f"[AuditLogSubscriber] Registered {len(AUDIT_EVENT_MAP)} event listeners"
    )
