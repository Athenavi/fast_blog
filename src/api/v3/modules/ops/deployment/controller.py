"""deployment 模块路由（T5-11 批次 6：部署脚本档案与执行日志，自 astro `ops/deployments` 能力域新建）

::

    GET    /api/v3/ops/deployment/script                脚本列表（分页 + keyword + script_type）
    POST   /api/v3/ops/deployment/script                新建脚本
    PUT    /api/v3/ops/deployment/script/{script_id}    更新脚本
    DELETE /api/v3/ops/deployment/script/{script_id}    删除脚本（连带清理其执行日志）
    GET    /api/v3/ops/deployment/log                   执行日志分页（script_id / status 可选过滤）
    GET    /api/v3/ops/deployment/log/{log_id}          单条日志详情
    DELETE /api/v3/ops/deployment/log/{log_id}          删除日志

权限码：``module_ops:deployment:view``（读）/ ``module_ops:deployment:edit``（写）。

**执行编排属后续二期**：真实拉起脚本（如 ``/script/{id}/execute``）属高危动作，
本期不做任何执行入口，只做脚本档案管理与执行日志查看。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.deployment.schema import (
    DeploymentScriptCreate,
    DeploymentScriptUpdate,
)
from src.api.v3.modules.ops.deployment.service import deployment_service

router = APIRouter(prefix="/deployment", tags=["ops-deployment"], route_class=OperationLogRoute)


@router.get("/script", response_model=ResponseModel, summary="部署脚本列表")
async def list_scripts(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    script_type: Optional[str] = Query(default=None),
) -> dict:
    items, total = await deployment_service.list_scripts(
        db, page=page, page_size=page_size, keyword=keyword, script_type=script_type
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/script", response_model=ResponseModel, summary="新建部署脚本")
async def create_script(
    payload: DeploymentScriptCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_EDIT),
) -> dict:
    return resp.success(
        await deployment_service.create_script(db, payload, created_by=current.id), msg="已创建"
    )


@router.put("/script/{script_id}", response_model=ResponseModel, summary="更新部署脚本")
async def update_script(
    script_id: int,
    payload: DeploymentScriptUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_EDIT),
) -> dict:
    return resp.success(await deployment_service.update_script(db, script_id, payload), msg="已保存")


@router.delete("/script/{script_id}", response_model=ResponseModel, summary="删除部署脚本")
async def delete_script(
    script_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_EDIT),
) -> dict:
    await deployment_service.delete_script(db, script_id)
    return resp.success(None, msg="已删除")


@router.get("/log", response_model=ResponseModel, summary="执行日志列表")
async def list_logs(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    script_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> dict:
    items, total = await deployment_service.list_logs(
        db, page=page, page_size=page_size, script_id=script_id, status=status
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/log/{log_id}", response_model=ResponseModel, summary="执行日志详情")
async def get_log(
    log_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_VIEW),
) -> dict:
    return resp.success(await deployment_service.get_log(db, log_id))


@router.delete("/log/{log_id}", response_model=ResponseModel, summary="删除执行日志")
async def delete_log(
    log_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.DEPLOYMENT_EDIT),
) -> dict:
    await deployment_service.delete_log(db, log_id)
    return resp.success(None, msg="已删除")
