"""维护模式中间件：命中维护时对非白名单请求返回 503

要点：

- **配置有 5 秒 TTL 缓存** —— 中间件在每个请求上跑，不能每请求查一次库；
  但也不能永久缓存（开关要尽快生效）。写配置的 API 会主动 ``invalidate_cache()``。
- **读配置失败按"不维护"处理**：维护模式自身的故障不该把整个站点拖挂（可用性优先）。
- 白名单路径（健康探针、登录、维护状态、docs）始终放行 —— 否则维护期间管理员连登录都进不去。
"""

import time
from typing import Any, Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.maintenance.service import (
    ALLOWED_PATH_PREFIXES,
    maintenance_service,
)

logger = get_logger("middleware.maintenance")

#: 配置缓存时长（秒）
CACHE_TTL_SECONDS = 5.0

_cache: Tuple[float, Optional[Dict[str, Any]]] = (0.0, None)


def invalidate_cache() -> None:
    """写配置后主动失效（让开关立即生效，不必等 TTL）"""
    global _cache
    _cache = (0.0, None)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def _cached_config() -> Dict[str, Any]:
    global _cache
    now = time.monotonic()
    timestamp, cached = _cache
    if cached is not None and now - timestamp < CACHE_TTL_SECONDS:
        return cached

    config: Dict[str, Any] = {"enabled": False}
    try:
        from src.utils.database.unified_manager import db_manager

        async with db_manager.get_session_no_auto_commit() as db:
            config = await maintenance_service.get_config(db)
    except Exception:  # noqa: BLE001 - 读失败按"不维护"处理，可用性优先
        logger.exception("维护模式配置读取失败，本次按不维护处理")
        return config

    _cache = (now, config)
    return config


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """维护模式拦截"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            return await call_next(request)

        config = await _cached_config()
        state = maintenance_service.evaluate(config, client_ip=_client_ip(request))
        if not state["active"]:
            return await call_next(request)

        response = JSONResponse(
            status_code=503,
            content={
                "success": False,
                "code": 503,
                "msg": state["message"],
                "data": {
                    "retry_after": state["retry_after"],
                    "scheduled_end": state["scheduled_end"],
                },
                "error": "Service Unavailable",
                "pagination": None,
            },
        )
        response.headers["Retry-After"] = str(state["retry_after"])
        return response
