"""log 模块业务逻辑

审计日志与登录安全全部委托给既有 service，v3 只做「参数归一化 + 响应整形」，
保证与 v2 的日志数据完全一致（同一批表、同一个 service）。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.security.audit_log_service import audit_log_service
from shared.services.users.login_security_service import login_security_service
from src.api.v3.core.logger import get_logger

logger = get_logger("log")


def _as_dict(item: Any) -> dict:
    """把 ORM 对象或字典统一成 dict（service 的返回形态可能两者都有）"""
    if isinstance(item, dict):
        return item
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return {
        key: getattr(item, key, None)
        for key in (
            "id", "user_id", "user_name", "action", "level", "resource_type",
            "resource_id", "description", "ip_address", "created_at",
        )
    }


class LogService:
    """审计日志与登录安全"""

    async def list_audit_logs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        level: Optional[str] = None,
        resource_type: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[dict], int]:
        result = await audit_log_service.get_logs(
            db,
            user_id=user_id,
            action=action,
            level=level,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=page_size,
        )
        if not isinstance(result, dict):
            return [], 0

        items = result.get("logs") or result.get("items") or result.get("data") or []
        total = result.get("total")
        if total is None:
            total = result.get("count", len(items))
        logs = [_as_dict(item) for item in items]
        if keyword:
            lowered = keyword.lower()
            logs = [
                log
                for log in logs
                if lowered in str(log.get("description") or "").lower()
                   or lowered in str(log.get("action") or "").lower()
                   or lowered in str(log.get("user_name") or "").lower()
            ]
        return logs, int(total)

    async def export_audit_logs(
        self,
        db: AsyncSession,
        *,
        output_format: str = "json",
        **filters: Any,
    ) -> Tuple[str, str]:
        content = await audit_log_service.export_logs(db, output_format=output_format, **filters)
        return output_format, content or ""

    async def cleanup_audit_logs(self, db: AsyncSession, days: int) -> int:
        deleted = await audit_log_service.cleanup_old_logs(db, days=days)
        return int(deleted or 0)

    async def locked_users(self, db: AsyncSession) -> List[dict]:
        users = await login_security_service.get_locked_users_async(db)
        return [_as_dict(user) for user in (users or [])]

    async def user_login_history(
        self, username: str, *, limit: int = 50, db: Optional[AsyncSession] = None
    ) -> List[dict]:
        history = await login_security_service.get_login_history_async(username, limit=limit, db=db)
        return [_as_dict(item) for item in (history or [])]

    async def user_security_stats(
        self, username: str, *, db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        stats = await login_security_service.get_security_stats_async(username, db=db)
        return stats if isinstance(stats, dict) else {}


log_service = LogService()
