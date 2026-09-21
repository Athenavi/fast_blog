"""ops.supervisor 模块路由（进程监督：登记 / 状态 / 受控启停 / 日志）

::

    GET    /api/v3/ops/supervisor/process                   登记项 + 实时状态（health/metrics）
    PUT    /api/v3/ops/supervisor/process                   整体保存登记（校验不过不落库）
    GET    /api/v3/ops/supervisor/process/{name}/health     三层健康检查（pid / 端口 / HTTP）
    GET    /api/v3/ops/supervisor/process/{name}/log        日志末尾 N 行（白名单目录）
    POST   /api/v3/ops/supervisor/process/{name}/start      启动（需 confirm=true）
    POST   /api/v3/ops/supervisor/process/{name}/stop       停止（需 confirm=true）
    POST   /api/v3/ops/supervisor/process/{name}/restart    重启（需 confirm=true）

权限码：``module_ops:supervisor:{view,config,execute}``。

**边界（实现里强制）**：只执行登记过的命令（API 不接受任意命令串）；启停/重启必须
``confirm=true``；日志只允许读 ``logs/`` 与 ``storage/logs/`` 下的文件；
未登记的动作 / 未登记的进程 / 探测或执行失败一律**如实回报原因**，不假装成功。

本模块替代仓库根的原 ``process_supervisor/``（含 9422 内嵌 HTML 管理页）——
进程生命周期归部署层（Docker / systemd），这里只做"看得见 + 按登记命令触发"。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.supervisor.schema import (
    SupervisorActionPayload,
    SupervisorConfigPayload,
)
from src.api.v3.modules.ops.supervisor.service import supervisor_service

router = APIRouter(prefix="/supervisor", tags=["ops-supervisor"], route_class=OperationLogRoute)


@router.get("/process", response_model=ResponseModel, summary="进程登记 + 实时状态")
async def list_processes(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_VIEW),
) -> dict:
    """每个登记项都带上探测结果（是否在跑、端口/HTTP 是否通）与可用时的 CPU/内存指标。"""
    return resp.success(await supervisor_service.list_processes(db))


@router.put("/process", response_model=ResponseModel, summary="保存进程登记（整体替换）")
async def save_processes(
    payload: SupervisorConfigPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_CONFIG),
) -> dict:
    """校验（重名 / 命令超长 / 路径越界）不通过时**不落库**，并返回 ``issues`` 清单。"""
    data = await supervisor_service.save_processes(db, payload)
    msg = "已保存" if not data.get("issues") else "校验未通过，未保存"
    return resp.success(data, msg=msg)


@router.get("/process/{name}/health", response_model=ResponseModel, summary="三层健康检查")
async def process_health(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_VIEW),
) -> dict:
    return resp.success(await supervisor_service.health(db, name))


@router.get("/process/{name}/log", response_model=ResponseModel, summary="进程日志（末尾 N 行）")
async def process_log(
    name: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_VIEW),
    lines: int = Query(default=200, ge=1, le=2000),
) -> dict:
    return resp.success(await supervisor_service.read_log(db, name, lines))


@router.post("/process/{name}/start", response_model=ResponseModel, summary="启动进程")
async def start_process(
    name: str,
    payload: SupervisorActionPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_EXECUTE),
) -> dict:
    """执行该登记项的 ``start_command``（真实执行部署命令，需 ``confirm=true``）。"""
    return resp.success(await supervisor_service.act(db, name, "start", confirm=payload.confirm))


@router.post("/process/{name}/stop", response_model=ResponseModel, summary="停止进程")
async def stop_process(
    name: str,
    payload: SupervisorActionPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_EXECUTE),
) -> dict:
    """执行该登记项的 ``stop_command``；如果名字就是本应用自身，请自行确认中断影响。"""
    return resp.success(await supervisor_service.act(db, name, "stop", confirm=payload.confirm))


@router.post("/process/{name}/restart", response_model=ResponseModel, summary="重启进程")
async def restart_process(
    name: str,
    payload: SupervisorActionPayload,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SUPERVISOR_EXECUTE),
) -> dict:
    """执行该登记项的 ``restart_command``；用于升级后使新代码生效。"""
    return resp.success(await supervisor_service.act(db, name, "restart", confirm=payload.confirm))
