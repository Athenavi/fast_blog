"""ai.workflow 模块路由（T5-11 批次 4：自 astro `admin/ai-workflows` 能力域新建）

::

    GET    /api/v3/ai/workflow                    执行记录列表
    DELETE /api/v3/ai/workflow/{workflow_id}      删除记录

权限码：``module_ai:workflow:view/delete``。
执行引擎为二期：status 流转（pending/processing/completed/failed）由后续接入的执行端负责。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
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


@router.delete("/{workflow_id}", response_model=ResponseModel, summary="删除工作流记录")
async def delete_workflow(
    workflow_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.AI_WORKFLOW_DELETE),
) -> dict:
    await ai_workflow_service.delete_workflow(db, workflow_id)
    return resp.success(None, msg="已删除")
