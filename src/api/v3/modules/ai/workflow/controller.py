"""ai.workflow 模块路由（T5-11 批次 4 新建；批次 20 接入**真实执行引擎**）

::

    GET    /api/v3/ai/workflow                    执行记录列表
    GET    /api/v3/ai/workflow/task-types         可用任务类型（下拉用）
    POST   /api/v3/ai/workflow/execute            发起任务（**真实调用模型**）
    POST   /api/v3/ai/workflow/{workflow_id}/retry 用原输入重跑
    DELETE /api/v3/ai/workflow/{workflow_id}      删除记录

权限码：``module_ai:workflow:view/delete/execute``。
静态路径（``/task-types``、``/execute``）注册在 ``/{workflow_id}`` 之前 —— 启动期会拦路径遮蔽。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ai.workflow.schema import WorkflowExecute
from src.api.v3.modules.ai.workflow.service import ai_workflow_service

router = APIRouter(prefix="/workflow", tags=["ai-workflow"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="AI 工作流记录列表")
async def list_workflows(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await ai_workflow_service.list_workflows(
        db, page=page, page_size=page_size, user_id=user_id,
        task_type=task_type, status=status, keyword=keyword,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/task-types", response_model=ResponseModel, summary="可用任务类型")
async def list_task_types(
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_VIEW),
) -> dict:
    return resp.success(ai_workflow_service.task_types())


@router.post("/execute", response_model=ResponseModel, summary="执行 AI 任务（真实调用）")
async def execute_workflow(
    payload: WorkflowExecute,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_EXECUTE),
) -> dict:
    """按 ``task_type`` 渲染提示词并真的调用模型；失败会落一条 failed 记录并带回原因。"""
    result = await ai_workflow_service.execute(db, payload)
    return resp.success(result, msg="执行完成")


@router.post("/{workflow_id}/retry", response_model=ResponseModel, summary="重跑任务")
async def retry_workflow(
    workflow_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_EXECUTE),
) -> dict:
    return resp.success(await ai_workflow_service.retry(db, workflow_id), msg="已重跑")


@router.delete("/{workflow_id}", response_model=ResponseModel, summary="删除工作流记录")
async def delete_workflow(
    workflow_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_DELETE),
) -> dict:
    await ai_workflow_service.delete_workflow(db, workflow_id)
    return resp.success(None, msg="已删除")
