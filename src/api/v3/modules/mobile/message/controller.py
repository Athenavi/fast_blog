"""mobile/message：前台站内信（表 ``private_messages``）

路由前缀：``/api/v3/mobile/message``

移动端用户接口：**仅需登录，不声明权限码**（与 ``mobile/article`` 等一致，
route_class 同样用 ``OperationLogRoute``；写端点登记在
``core/permission/audit.py`` 的 ``EXEMPT_WRITE_ENDPOINTS``——仅认证且只操作本人数据）。

行为要点（详见 ``service.py``）：

  - 双向软删：``is_deleted_by_sender`` / ``is_deleted_by_recipient`` 各自独立，
    一方删除后自己侧不可见，对方仍可见
  - 归属不符一律 404（不泄露存在性）：已读标记仅收件人、删除仅收发双方
  - 静态路径（``/contacts``、``/list``）前置注册，避免被 ``/{message_id}`` 遮蔽
"""

from fastapi import APIRouter, Depends, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.mobile.message.schema import MobileMessageCreate
from src.api.v3.modules.mobile.message.service import mobile_message_service
from src.auth.auth_deps import jwt_required_dependency

router = APIRouter(prefix="/message", tags=["mobile-message"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 会话
@router.get("/contacts", response_model=ResponseModel, summary="会话列表（需登录）")
async def list_contacts(
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """与我相关的会话（排除我已删除的消息），最近活跃在前。"""
    return resp.success(await mobile_message_service.list_contacts(db, user_id=user.id))


@router.get("/list", response_model=ResponseModel, summary="与某用户的私信记录（需登录，时间正序）")
async def list_conversation(
    db: DBSession,
    peer_id: int = Query(description="对方用户 ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    user=Depends(jwt_required_dependency),
) -> dict:
    items, total = await mobile_message_service.list_conversation(
        db, user_id=user.id, peer_id=peer_id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


# ---------------------------------------------------------------- 发送
@router.post("", response_model=ResponseModel, summary="发送私信（需登录）")
async def send_message(
    payload: MobileMessageCreate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """发给自己 400；收件人不存在 404；可带 ``parent_message`` 回复某条消息。"""
    return resp.success(
        await mobile_message_service.send(db, user_id=user.id, payload=payload), msg="已发送"
    )


# ---------------------------------------------------------------- 已读 / 删除
@router.post("/{message_id}/read", response_model=ResponseModel, summary="标记消息已读（仅收件人）")
async def mark_message_read(
    message_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """仅收件人可标记；非本人收件按约定返回 404（不泄露存在性）。"""
    return resp.success(
        await mobile_message_service.mark_read(db, user_id=user.id, message_id=message_id)
    )


@router.delete(
    "/{message_id}", response_model=ResponseModel, summary="删除消息（仅收发双方，双向软删）"
)
async def delete_message(
    message_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """只置当前用户一侧的软删标志，对方的可见性不受影响。"""
    await mobile_message_service.delete(db, user_id=user.id, message_id=message_id)
    return resp.success(None, msg="已删除")
