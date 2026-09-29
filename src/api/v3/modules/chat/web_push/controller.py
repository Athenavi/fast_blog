"""chat.web_push 模块路由（chat 域：浏览器推送 / Web Push）

::

    GET  /api/v3/chat/web_push/vapid-public-key    VAPID 公钥下发（公开；未配置时如实标注）
    POST /api/v3/chat/web_push/subscribe           登记订阅（仅认证；只操作本人）
    POST /api/v3/chat/web_push/unsubscribe         退订（仅认证；只操作本人）
    GET  /api/v3/chat/web_push/subscriptions       我的订阅列表（仅认证）
    POST /api/v3/chat/web_push/send                按用户推送（管理端）
    POST /api/v3/chat/web_push/broadcast           广播推送（管理端）
    GET  /api/v3/chat/web_push/stats               订阅统计（管理端）
    POST /api/v3/chat/web_push/cleanup             清理失效 / 过期订阅（管理端）

权限码（**如实说明借用**）：chat 域**没有** ``web_push`` 专属权限码，管理端端点借用 ops 域的
通知码 —— 推送发送 / 广播 / 清理用 ``module_ops:notification:edit``（"管理通知"），统计用
``module_ops:notification:view``（"查看通知"）。订阅登记 / 退订 / 我的列表是**仅需认证且只操作本人**
的前台端点，不发权限码。

**写操作审计**：``POST /subscribe`` 与 ``POST /unsubscribe`` 是仅认证的无码写端点，按既有约定
（如 ``chat/message``、``gamification/points``）应登记进 ``src/api/v3/core/permission/audit.py`` 的
``EXEMPT_WRITE_ENDPOINTS``。本任务写入范围仅限本模块目录，故**未自行登记**，需父代理补登：

    ("POST", "/api/v3/chat/web_push/subscribe"):   "登记本人推送订阅（仅认证；只操作本人）",
    ("POST", "/api/v3/chat/web_push/unsubscribe"): "退订本人推送（仅认证；只操作本人）",

未登记时，启动期权限审计（``audit_permissions``）会把它们列为「写操作未声明权限码」告警；
``PERMISSION_AUDIT_STRICT=1`` 下会**拒绝启动**。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.chat.web_push.schema import (
    WebPushBroadcastIn,
    WebPushCleanupIn,
    WebPushSendIn,
    WebPushSubscriptionIn,
    WebPushUnsubscribeIn,
)
from src.api.v3.modules.chat.web_push.service import web_push_service

router = APIRouter(prefix="/web_push", tags=["chat-web-push"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 公开
@router.get("/vapid-public-key", response_model=ResponseModel, summary="VAPID 公钥下发")
async def vapid_public_key() -> dict:
    """返回 VAPID 公钥供前端 ``pushManager.subscribe`` 使用。

    公钥是**公开信息**，故本端点匿名可读。后端未配置推送（缺 ``pywebpush`` 或 VAPID 密钥）时
    ``configured=False`` 且 ``reason`` 说明缺什么 —— **不会**返回编造的公钥。
    """
    return resp.success(web_push_service.vapid_public_key())


# ---------------------------------------------------------------- 本人订阅
@router.post("/subscribe", response_model=ResponseModel, summary="登记推送订阅")
async def subscribe(
    payload: WebPushSubscriptionIn,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """登记（或更新）**当前用户**的一条浏览器推送订阅。

    仅认证，只操作本人数据；同一 ``endpoint`` 重复登记幂等（更新 keys / user_agent）。
    ``endpoint`` / ``keys`` 结构非法会返回 400。
    """
    return resp.success(await web_push_service.subscribe(db, current.id, payload), msg="已订阅")


@router.post("/unsubscribe", response_model=ResponseModel, summary="退订推送")
async def unsubscribe(
    payload: WebPushUnsubscribeIn,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """退订**当前用户**的推送。

    给 ``subscription_id`` 或 ``endpoint`` 精确退订；两者都省略则退订本人全部订阅。
    """
    return resp.success(await web_push_service.unsubscribe(db, current.id, payload), msg="已退订")


@router.get("/subscriptions", response_model=ResponseModel, summary="我的订阅列表")
async def my_subscriptions(db: DBSession, current: CurrentUser) -> dict:
    """列出**当前用户**的订阅（不返回 keys 公钥材料）。"""
    return resp.success(await web_push_service.list_subscriptions(db, current.id))


# ---------------------------------------------------------------- 管理端
@router.post("/send", response_model=ResponseModel, summary="按用户推送")
async def send_push(
    payload: WebPushSendIn,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.NOTIFICATION_EDIT),
) -> dict:
    """向指定用户推送一条通知（**真实发送**）。

    推送依赖 ``pywebpush`` + VAPID 密钥；缺任一时**返回 400「未配置」**而非伪造成功。
    用户不存在 → 404；用户无订阅 → 返回空结果（``sent=0``）。
    """
    return resp.success(
        await web_push_service.send_to_user(db, payload, operator_id=current.id), msg="推送完成"
    )


@router.post("/broadcast", response_model=ResponseModel, summary="广播推送")
async def broadcast_push(
    payload: WebPushBroadcastIn,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.NOTIFICATION_EDIT),
) -> dict:
    """向**全部已有订阅**的用户广播推送（真实发送；未配置 → 400）。

    本项目无「主题 / 分组」表，故不提供按主题分流（如实不做）。
    """
    return resp.success(
        await web_push_service.broadcast(db, payload, operator_id=current.id), msg="广播完成"
    )


@router.get("/stats", response_model=ResponseModel, summary="订阅统计")
async def push_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NOTIFICATION_VIEW),
) -> dict:
    """订阅统计（真实从 ``system_settings`` 聚合）+ VAPID 配置状态。"""
    return resp.success(await web_push_service.stats(db))


@router.post("/cleanup", response_model=ResponseModel, summary="清理失效/过期订阅")
async def cleanup_subscriptions(
    payload: WebPushCleanupIn,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.NOTIFICATION_EDIT),
) -> dict:
    """清理超过 ``max_age_days`` 的过期订阅与结构非法的订阅（真实删除）。

    ``dry_run=true`` 时只统计不删除。
    """
    return resp.success(
        await web_push_service.cleanup(
            db, max_age_days=payload.max_age_days, dry_run=payload.dry_run
        ),
        msg="清理完成",
    )
