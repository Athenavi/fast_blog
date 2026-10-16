"""health 模块路由

路径：``/api/v3/system/health/live``、``/ready``、``/site-report``、``/web-vitals``
（域前缀 ``/system`` 由 ``core/discover.py`` 挂载，模块前缀在此声明。）

``live`` / ``ready`` 是给编排系统用的**公开**探针（不含敏感信息）；
``site-report`` 会暴露 SECRET_KEY / DEBUG / CORS 等配置状态，因此需要登录 + ``monitor:view``。

``web-vitals`` 是 RUM 上报入口（前端 ``navigator.sendBeacon`` 批量发数组，访客未登录也要能上报），
因此同样公开；它**不放在 monitor 模块**：monitor 的路由挂了 ``OperationLogRoute``，
高频上报会把审计日志刷满。查询 CWV 汇总仍需 ``monitor:view``。
"""

from typing import List

from fastapi import APIRouter, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.modules.system.health.schema import WebVitalSample
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


# ─────────────────────────── 前端性能（RUM / Web Vitals）───────────────────────────
@router.post("/web-vitals", response_model=ResponseModel, summary="[公开] 前端 Web Vitals 上报")
async def ingest_web_vitals(samples: List[WebVitalSample], request: Request) -> dict:
    """接收前端批量上报的核心指标（sendBeacon 发的是裸数组）

    公开端点：访客未登录也会上报。单次最多 50 条，只接受 LCP/INP/CLS/FCP/TTFB 五个指标，
    数值范围由 ``WebVitalSample`` 校验。
    """
    if len(samples) > health_service.max_vitals_per_request:
        return resp.fail(
            f"单次最多 {health_service.max_vitals_per_request} 条样本",
            code=resp.CODE_BAD_REQUEST,
        )
    result = health_service.ingest_web_vitals(
        samples, user_agent=request.headers.get("user-agent", "")
    )
    return resp.success(result, msg="accepted")


@router.get("/web-vitals/summary", response_model=ResponseModel, summary="前端性能（CWV）汇总")
async def web_vitals_summary(
    _current: CurrentUser,
    _perm=AuthControl(codes.MONITOR_VIEW),
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=10, ge=1, le=100, description="最慢页面返回条数"),
) -> dict:
    """整体 Core Web Vitals 统计与最慢页面（数据来自进程内 RUM 采集）"""
    return resp.success(health_service.web_vitals_summary(hours=hours, limit=limit))
