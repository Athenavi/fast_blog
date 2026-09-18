"""health 模块路由

路径：``/api/v3/system/health/live``、``/api/v3/system/health/ready``
（域前缀 ``/system`` 由 ``core/discover.py`` 挂载，模块前缀在此声明。）
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
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
