"""操作日志路由类（照搬 FastApiAdmin ``app/core/router_class.py`` 的 ``OperationLogRoute`` 思路）

用法::

    from src.api.v3.core.router_class import OperationLogRoute

    router = APIRouter(prefix="/user", tags=["system-user"], route_class=OperationLogRoute)

行为：**写操作**（POST/PUT/PATCH/DELETE）在响应返回后异步写一条 ``audit_logs`` 记录，
复用项目已有的 ``shared/services/security/audit_log_service``。

设计约束：
  - 只记录写操作，GET/HEAD/OPTIONS 不落库（避免读操作淹没审计表）
  - 异步 fire-and-forget：审计失败绝不影响响应（与官方实现一致的取舍）
  - 未认证请求（user_id 为空）也记录，便于追踪异常访问
"""

import asyncio
from typing import Callable, Set

from fastapi import Request, Response
from fastapi.routing import APIRoute

from src.api.v3.core.logger import get_logger

logger = get_logger("operation_log")

#: 防止任务被 GC（asyncio 只持弱引用）
_BACKGROUND_TASKS: Set[asyncio.Task] = set()

_ACTION_BY_METHOD = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class OperationLogRoute(APIRoute):
    """自动写操作日志的路由类"""

    def get_route_handler(self) -> Callable:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            response = await original_handler(request)
            if request.method.upper() in _ACTION_BY_METHOD and response.status_code < 400:
                task = asyncio.create_task(self._write_log(request))
                _BACKGROUND_TASKS.add(task)
                task.add_done_callback(_BACKGROUND_TASKS.discard)
            return response

        return custom_handler

    async def _write_log(self, request: Request) -> None:
        try:
            await _log_operation(request, self.path)
        except Exception:  # noqa: BLE001 - 审计失败不得影响业务
            logger.exception("写操作日志失败 path=%s", self.path)


async def _log_operation(request: Request, route_path: str) -> None:
    from shared.services.security.audit_log_service import (
        AuditLogAction,
        AuditLogLevel,
        audit_log_service,
    )
    from src.utils.database.unified_manager import db_manager

    state_user = getattr(request.state, "user", None) or getattr(request.state, "current_user", None)
    user_id = getattr(state_user, "id", None)
    user_name = getattr(state_user, "username", None)

    method = request.method.upper()
    resource_type = _resource_of(route_path)
    path_params = getattr(request, "path_params", {}) or {}

    async with db_manager.get_session() as db:
        await audit_log_service.log_action(
            db=db,
            user_id=user_id,
            user_name=user_name,
            action=AuditLogAction.UPDATE if method in {"PUT", "PATCH"} else (
                AuditLogAction.DELETE if method == "DELETE" else AuditLogAction.CREATE
            ),
            level=AuditLogLevel.INFO,
            resource_type=resource_type,
            resource_id=_first_path_param(path_params),
            description=f"{method} {request.url.path}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )


def _resource_of(route_path: str) -> str:
    """把 ``/api/v3/system/user/{user_id}`` 归纳为 ``system.user``"""
    parts = [p for p in route_path.split("/") if p and not p.startswith("{")]
    # 去掉 api / v3 前缀
    if len(parts) >= 2 and parts[0] == "api":
        parts = parts[2:]
    return ".".join(parts) or "unknown"


def _first_path_param(path_params: dict):
    for value in path_params.values():
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None
