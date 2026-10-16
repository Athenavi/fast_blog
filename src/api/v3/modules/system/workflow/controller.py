"""system.workflow 模块路由（通用工作流引擎）

::

    GET    /api/v3/system/workflow/definition                 定义列表
    POST   /api/v3/system/workflow/definition                 注册 / 覆盖定义
    POST   /api/v3/system/workflow/definition/validate        只校验不保存
    GET    /api/v3/system/workflow/definition/{workflow_id}   单个定义
    DELETE /api/v3/system/workflow/definition/{workflow_id}   删除定义
    POST   /api/v3/system/workflow/instance                   创建实例
    GET    /api/v3/system/workflow/instance                   实例列表
    GET    /api/v3/system/workflow/instance/{instance_id}     单个实例
    POST   /api/v3/system/workflow/instance/{id}/execute      逐步执行
    POST   /api/v3/system/workflow/instance/{id}/approve      通过审批并继续
    POST   /api/v3/system/workflow/instance/{id}/reject       拒绝审批
    POST   /api/v3/system/workflow/instance/{id}/cancel       取消实例
    GET    /api/v3/system/workflow/history                    执行历史

权限：查看用 ``setting:view``，写入 / 执行用 ``setting:edit``。

定义持久化到 ``system_settings``（键 ``workflow.definitions``），实例与执行记录落到
键 ``workflow.instances``（JSON 数组，最多保留最近 200 条）。
"""

from typing import Optional

from fastapi import APIRouter, Body, Path, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.workflow.schema import (
    WorkflowApproval,
    WorkflowDefinitionSave,
    WorkflowDefinitionValidate,
    WorkflowInstanceCreate,
)
from src.api.v3.modules.system.workflow.service import (
    validate_definition as validate_workflow_definition,
)
from src.api.v3.modules.system.workflow.service import workflow_engine_service

router = APIRouter(
    prefix="/workflow", tags=["system-workflow"], route_class=OperationLogRoute
)


# ------------------------------------------------------------ 定义
@router.get("/definition", response_model=ResponseModel, summary="工作流定义列表")
async def list_definitions(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await workflow_engine_service.list_definitions(db))


@router.post("/definition", response_model=ResponseModel, summary="注册 / 覆盖工作流定义")
async def register_definition(
    db: DBSession,
    current: CurrentUser,
    payload: WorkflowDefinitionSave,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """非法定义（重复 id / 悬空 next / 多入口 / 有环 / condition 缺分支等）返回 400 并说明原因"""
    return resp.success(
        await workflow_engine_service.register_definition(
            db, payload.workflow_id, payload.definition, user_id=getattr(current, "id", None)
        ),
        msg="已保存",
    )


@router.post("/definition/validate", response_model=ResponseModel, summary="只校验工作流定义（不保存）")
async def validate_definition(
    payload: WorkflowDefinitionValidate,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    normalized = validate_workflow_definition(payload.definition)
    return resp.success({"valid": True, "workflow_id": normalized.get("workflow_id"), "nodes": normalized["nodes"]})


@router.get("/definition/{workflow_id}", response_model=ResponseModel, summary="单个工作流定义")
async def get_definition(
    db: DBSession,
    _current: CurrentUser,
    workflow_id: str = Path(..., min_length=1, max_length=100),
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await workflow_engine_service.get_definition(db, workflow_id))


@router.delete("/definition/{workflow_id}", response_model=ResponseModel, summary="删除工作流定义")
async def delete_definition(
    db: DBSession,
    _current: CurrentUser,
    workflow_id: str = Path(..., min_length=1, max_length=100),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    await workflow_engine_service.delete_definition(db, workflow_id)
    return resp.success(None, msg="已删除")


# ------------------------------------------------------------ 实例
@router.post("/instance", response_model=ResponseModel, summary="创建工作流实例")
async def create_instance(
    db: DBSession,
    _current: CurrentUser,
    payload: WorkflowInstanceCreate,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    return resp.success(
        await workflow_engine_service.create_instance(db, payload.workflow_id, payload.context),
        msg="已创建",
    )


@router.get("/instance", response_model=ResponseModel, summary="工作流实例列表")
async def list_instances(
    db: DBSession,
    _current: CurrentUser,
    status: Optional[str] = Query(default=None, description="按状态过滤，如 running / pending_approval"),
    limit: int = Query(default=50, ge=1, le=500),
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(
        await workflow_engine_service.list_instances(db, status=status, limit=limit)
    )


@router.get("/instance/{instance_id}", response_model=ResponseModel, summary="单个工作流实例")
async def get_instance(
    db: DBSession,
    _current: CurrentUser,
    instance_id: str = Path(..., min_length=1),
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await workflow_engine_service.get_instance(db, instance_id))


@router.post("/instance/{instance_id}/execute", response_model=ResponseModel, summary="逐步执行工作流实例")
async def execute_instance(
    db: DBSession,
    _current: CurrentUser,
    instance_id: str = Path(..., min_length=1),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """逐节点真实执行并落库；遇到 ``approval`` 节点会停在 ``pending_approval``"""
    return resp.success(await workflow_engine_service.execute(db, instance_id), msg="已执行")


@router.post("/instance/{instance_id}/approve", response_model=ResponseModel, summary="通过审批并继续")
async def approve_instance(
    db: DBSession,
    current: CurrentUser,
    instance_id: str = Path(..., min_length=1),
    payload: Optional[WorkflowApproval] = Body(default=None),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    comment = payload.comment if payload else None
    return resp.success(
        await workflow_engine_service.approve(
            db, instance_id, comment=comment, user_id=getattr(current, "id", None)
        ),
        msg="已通过",
    )


@router.post("/instance/{instance_id}/reject", response_model=ResponseModel, summary="拒绝审批")
async def reject_instance(
    db: DBSession,
    current: CurrentUser,
    instance_id: str = Path(..., min_length=1),
    payload: Optional[WorkflowApproval] = Body(default=None),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    comment = payload.comment if payload else None
    return resp.success(
        await workflow_engine_service.reject(
            db, instance_id, comment=comment, user_id=getattr(current, "id", None)
        ),
        msg="已拒绝",
    )


@router.post("/instance/{instance_id}/cancel", response_model=ResponseModel, summary="取消工作流实例")
async def cancel_instance(
    db: DBSession,
    _current: CurrentUser,
    instance_id: str = Path(..., min_length=1),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    return resp.success(await workflow_engine_service.cancel(db, instance_id), msg="已取消")


# ------------------------------------------------------------ 历史
@router.get("/history", response_model=ResponseModel, summary="工作流执行历史")
async def workflow_history(
    db: DBSession,
    _current: CurrentUser,
    instance_id: Optional[str] = Query(default=None, description="只看某个实例的历史"),
    limit: int = Query(default=100, ge=1, le=500),
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(
        await workflow_engine_service.history(db, instance_id=instance_id, limit=limit)
    )
