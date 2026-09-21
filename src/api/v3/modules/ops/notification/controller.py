"""notification 模块路由（全部以当前用户为 recipient）

::

    GET    /api/v3/ops/notification                  我的通知列表
    GET    /api/v3/ops/notification/unread-count     未读数量
    POST   /api/v3/ops/notification/read-all         全部标记已读
    POST   /api/v3/ops/notification/batch/read       批量标记已读
    POST   /api/v3/ops/notification/batch/delete     批量删除
    DELETE /api/v3/ops/notification/clean            清理已读
    POST   /api/v3/ops/notification/{id}/read        标记单条已读
    DELETE /api/v3/ops/notification/{id}             删除单条

``/unread-count``、``/read-all``、``/clean`` 是静态路径，必须注册在 ``/{notification_id}`` 之前。

权限：仅需登录；服务层强制 ``recipient == 当前用户``。
"""

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import CurrentUser, DBSession, PageDep
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.modules.ops.notification.schema import NotificationBatchRequest
from src.api.v3.modules.ops.notification.service import notification_service

router = APIRouter(prefix="/notification", tags=["ops-notification"])


@router.get("", response_model=ResponseModel, summary="我的通知列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 通知列表",
)
async def list_notifications(
    page: PageDep,
    db: DBSession,
    current: CurrentUser,
    unread_only: bool = Query(default=False, description="仅未读"),
) -> dict:
    items, total = await notification_service.list_for_user(
        db,
        user_id=current.id,
        page=page.page,
        page_size=page.page_size,
        unread_only=unread_only,
        order=page.order,
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.get("/unread-count", response_model=ResponseModel, summary="未读通知数量")
async def unread_count(db: DBSession, current: CurrentUser) -> dict:
    return resp.success({"unread": await notification_service.unread_count(db, user_id=current.id)})


@router.post("/read-all", response_model=ResponseModel, summary="全部标记已读")
async def read_all(db: DBSession, current: CurrentUser) -> dict:
    affected = await notification_service.mark_all_read(db, user_id=current.id)
    return resp.success({"affected": affected}, msg=f"已标记 {affected} 条")


@router.delete("/clean", response_model=ResponseModel, summary="清理已读通知")
async def clean_notifications(db: DBSession, current: CurrentUser) -> dict:
    affected = await notification_service.clean_read(db, user_id=current.id)
    return resp.success({"affected": affected}, msg=f"已清理 {affected} 条")


@router.post("/batch/read", response_model=ResponseModel, summary="批量标记已读")
async def batch_mark_read(
    payload: NotificationBatchRequest,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    affected = await notification_service.batch_mark_read(db, user_id=current.id, ids=payload.ids)
    return resp.success({"affected": affected}, msg=f"已标记 {affected} 条")


@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除通知")
async def batch_delete_notifications(
    payload: NotificationBatchRequest,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    affected = await notification_service.batch_delete(db, user_id=current.id, ids=payload.ids)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 条")


@router.post("/{notification_id}/read", response_model=ResponseModel, summary="标记单条已读")
async def mark_read(notification_id: int, db: DBSession, current: CurrentUser) -> dict:
    if not await notification_service.mark_read(
        db, user_id=current.id, notification_id=notification_id
    ):
        raise NotFoundError("通知不存在")
    return resp.success(None, msg="已标记已读")


@router.delete("/{notification_id}", response_model=ResponseModel, summary="删除通知")
async def delete_notification(notification_id: int, db: DBSession, current: CurrentUser) -> dict:
    if not await notification_service.delete(
        db, user_id=current.id, notification_id=notification_id
    ):
        raise NotFoundError("通知不存在")
    return resp.success(None, msg="已删除")
