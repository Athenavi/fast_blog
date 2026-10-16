"""webhook 模块路由

::

    GET    /api/v3/ops/webhook                列表
    POST   /api/v3/ops/webhook                创建
    GET    /api/v3/ops/webhook/events         可订阅事件（静态路径，必须先注册）
    GET    /api/v3/ops/webhook/{webhook_id}   详情
    PUT    /api/v3/ops/webhook/{webhook_id}   更新
    DELETE /api/v3/ops/webhook/{webhook_id}   删除
    POST   /api/v3/ops/webhook/{webhook_id}/test  触发测试投递

权限码：``settings:view`` / ``settings:edit``
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.ops.webhook.schema import WebhookCreate, WebhookUpdate
from src.api.v3.modules.ops.webhook.service import webhook_ops_service

router = APIRouter(prefix="/webhook", tags=["ops-webhook"], route_class=OperationLogRoute)


# ─────────────────────────── 静态路径优先 ───────────────────────────
@router.get("/events", response_model=ResponseModel, summary="可订阅事件清单")
async def available_events(
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_VIEW),
) -> dict:
    return resp.success(webhook_ops_service.available_events())


# ─────────────────────────── 列表 / 创建 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="Webhook 列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] Webhook 列表",
)
async def list_webhooks(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_VIEW),
) -> dict:
    items = await webhook_ops_service.list_webhooks(db)
    return resp.success_page(items, len(items), 1, len(items) or 1)


@router.post("", response_model=ResponseModel, summary="创建 Webhook")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建 Webhook",
)
async def create_webhook(
    payload: WebhookCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_EDIT),
) -> dict:
    return resp.success(await webhook_ops_service.create_webhook(db, payload), msg="创建成功")


# ─────────────────────────── 详情 / 更新 / 删除 / 测试 ───────────────────────────
@router.get("/{webhook_id}", response_model=ResponseModel, summary="Webhook 详情")
async def get_webhook(
    webhook_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_VIEW),
) -> dict:
    return resp.success(await webhook_ops_service.get_webhook(db, webhook_id))


@router.put("/{webhook_id}", response_model=ResponseModel, summary="更新 Webhook")
async def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_EDIT),
) -> dict:
    return resp.success(
        await webhook_ops_service.update_webhook(db, webhook_id, payload), msg="更新成功"
    )


@router.delete("/{webhook_id}", response_model=ResponseModel, summary="删除 Webhook")
async def delete_webhook(
    webhook_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_EDIT),
) -> dict:
    await webhook_ops_service.delete_webhook(db, webhook_id)
    return resp.success(None, msg="已删除")


@router.post("/{webhook_id}/test", response_model=ResponseModel, summary="触发测试投递")
async def test_webhook(
    webhook_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.WEBHOOK_EDIT),
) -> dict:
    result = await webhook_ops_service.test_webhook(db, webhook_id)
    return resp.success(result, msg="已触发测试投递" if result["triggered"] else "触发失败")
