"""health 模块路由

路径：``/api/v3/system/health/live``、``/ready``、``/site-report``
（域前缀 ``/system`` 由 ``core/discover.py`` 挂载，模块前缀在此声明。）

``live`` / ``ready`` 是给编排系统用的**公开**探针（不含敏感信息）；
``site-report`` 会暴露 SECRET_KEY / DEBUG / CORS 等配置状态，因此需要登录 + ``monitor:view``。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.modules.system.health.service import health_service

router = APIRouter(prefix="/health", tags=["system-health"])


@router.get("/live", response_model=ResponseModel, summary="存活探针")
async def live() -> dict:
    """进程存活检查：不触碰任何外部依赖"""
    return resp.success(health_service.build_payload(), msg="alive")


@router.get("/ready", response_model=ResponseModel, summary="就绪探针")
async def ready(db: DBSession) -> dict:
    """就绪检查：包含一次数据库连通性探测"""
    available, detail = await health_service.probe_database(db)
    payload = health_service.build_payload()
    payload["checks"] = {"database": detail}
    if not available:
        payload["status"] = "degraded"
        return resp.fail("数据库不可用", code=resp.CODE_SERVER_ERROR, data=payload)
    return resp.success(payload, msg="ready")


@router.get("/site-report", response_model=ResponseModel, summary="站点健康报告")
async def site_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    format: str = Query(default="json", pattern="^(json|text)$", description="json 或 text"),
) -> dict:
    """站点健康检查（系统 / 数据库 / 存储 / 安全 / 性能），复用 ``SiteHealthService``"""
    from shared.services.system.site_health import site_health_service

    if format == "text":
        return resp.success({"report": await site_health_service.generate_report("text", db)})
    return resp.success(await site_health_service.run_full_check(db))
