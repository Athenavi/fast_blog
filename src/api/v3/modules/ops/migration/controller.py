"""migration 模块路由（T5-11 批次 2：自 astro `admin/migration` 能力域新建）

::

    GET    /api/v3/ops/migration                        任务列表
    POST   /api/v3/ops/migration                        新建任务
    PUT    /api/v3/ops/migration/{task_id}              更新任务
    DELETE /api/v3/ops/migration/{task_id}              删除任务
    POST   /api/v3/ops/migration/{task_id}/start        启动任务
    POST   /api/v3/ops/migration/{task_id}/cancel       取消任务
    GET    /api/v3/ops/migration/{task_id}/log          任务日志

权限码：``module_ops:migration:view/create/edit/delete``。
执行引擎为二期（``start`` 仅流转状态，见 service docstring）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.migration.schema import MigrationTaskCreate, MigrationTaskUpdate
from src.api.v3.modules.ops.migration.service import migration_service

router = APIRouter(prefix="/migration", tags=["ops-migration"], route_class=OperationLogRoute)


@router.get("", response_model=ResponseModel, summary="任务列表")
async def list_tasks(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, description="pending/running/completed/cancelled/failed"),
) -> dict:
    items, total = await migration_service.list_tasks(
        db, page=page, page_size=page_size, keyword=keyword, status=status
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="新建任务")
async def create_task(
    payload: MigrationTaskCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_CREATE),
) -> dict:
    return resp.success(
        await migration_service.create_task(db, payload, user_id=current.id), msg="已创建"
    )


@router.put("/{task_id}", response_model=ResponseModel, summary="更新任务")
async def update_task(
    task_id: int,
    payload: MigrationTaskUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_EDIT),
) -> dict:
    return resp.success(await migration_service.update_task(db, task_id, payload), msg="已保存")


@router.delete("/{task_id}", response_model=ResponseModel, summary="删除任务")
async def delete_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_DELETE),
) -> dict:
    await migration_service.delete_task(db, task_id)
    return resp.success(None, msg="已删除")


@router.post("/{task_id}/start", response_model=ResponseModel, summary="启动任务")
async def start_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_EDIT),
) -> dict:
    return resp.success(await migration_service.start_task(db, task_id), msg="已启动")


@router.post("/{task_id}/cancel", response_model=ResponseModel, summary="取消任务")
async def cancel_task(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_EDIT),
) -> dict:
    return resp.success(await migration_service.cancel_task(db, task_id), msg="已取消")


@router.get("/{task_id}/log", response_model=ResponseModel, summary="任务日志")
async def list_logs(
    task_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.MIGRATION_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    items, total = await migration_service.list_logs(db, task_id, page=page, page_size=page_size)
    return resp.success_page(items, total, page, page_size)
