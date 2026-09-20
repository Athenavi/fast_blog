"""collaboration 模块路由（content 域：工作区 / 任务 / 团队评论 / 协作邀请 / yjs 协同）

::

    # 工作区（worktree）
    GET    /api/v3/content/collaboration/workspace
    POST   /api/v3/content/collaboration/workspace
    GET    /api/v3/content/collaboration/workspace/by-slug/{slug}
    GET    /api/v3/content/collaboration/workspace/{workspace_id}
    PUT    /api/v3/content/collaboration/workspace/{workspace_id}
    DELETE /api/v3/content/collaboration/workspace/{workspace_id}
    GET    /api/v3/content/collaboration/workspace/{workspace_id}/member
    POST   /api/v3/content/collaboration/workspace/{workspace_id}/member
    PUT    /api/v3/content/collaboration/workspace/{workspace_id}/member/{member_user_id}
    DELETE /api/v3/content/collaboration/workspace/{workspace_id}/member/{member_user_id}
    GET    /api/v3/content/collaboration/workspace/{workspace_id}/task
    POST   /api/v3/content/collaboration/workspace/{workspace_id}/task
    PUT    /api/v3/content/collaboration/task/{task_id}
    DELETE /api/v3/content/collaboration/task/{task_id}
    # 团队评论
    GET    /api/v3/content/collaboration/comment                    按内容查评论
    GET    /api/v3/content/collaboration/comment/mentions           @ 到我
    GET    /api/v3/content/collaboration/comment/statistics        统计
    POST   /api/v3/content/collaboration/comment                    发表评论
    PUT    /api/v3/content/collaboration/comment/{comment_id}
    DELETE /api/v3/content/collaboration/comment/{comment_id}
    POST   /api/v3/content/collaboration/comment/{comment_id}/resolve
    # 协作邀请
    GET    /api/v3/content/collaboration/invite
    POST   /api/v3/content/collaboration/invite
    POST   /api/v3/content/collaboration/invite/accept
    GET    /api/v3/content/collaboration/invite/{invite_id}
    DELETE /api/v3/content/collaboration/invite/{invite_id}
    # yjs 协同
    GET    /api/v3/content/collaboration/yjs/rooms                  本进程活跃房间
    POST   /api/v3/content/collaboration/yjs/document/{document_id}/save
    WS     /api/v3/content/collaboration/yjs/ws/{document_id}

权限码：``module_content:collaboration:{view,create,edit,delete}``。

**WebSocket 是本模块唯一的非 HTTP 端点**（也是整个 v3 的第一个）：浏览器 WebSocket API
无法自定义请求头，因此鉴权按「Cookie ``access_token`` → 子协议 ``bearer.<token>`` →
query ``token``」三级回退（query 会进访问日志，属最次选）。鉴权失败**直接以 4401 关闭**，
不像 v2 那样「解析失败也放行」。
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pycrdt import YMessageType, create_sync_message, handle_sync_message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article_content import ArticleContent
from shared.models.article.article_revision import ArticleRevision
from shared.models.user import User
from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.exceptions import UnauthorizedError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.core.security import decode_token
from src.api.v3.modules.content.collaboration.comment_service import comment_service
from src.api.v3.modules.content.collaboration.invite_service import invite_service
from src.api.v3.modules.content.collaboration.schema import (
    CommentCreate,
    CommentUpdate,
    DocumentSaveRequest,
    InviteAcceptRequest,
    InviteCreate,
    MemberAdd,
    MemberRoleUpdate,
    TaskCreate,
    TaskUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from src.api.v3.modules.content.collaboration.workspace_service import (
    task_service,
    workspace_service,
)
from src.api.v3.modules.content.collaboration.yjs_service import room_registry

logger = get_logger("content.collaboration")

router = APIRouter(prefix="/collaboration", tags=["content-collaboration"], route_class=OperationLogRoute)

_VIEW = AuthControl(codes.COLLABORATION_VIEW)
_CREATE = AuthControl(codes.COLLABORATION_CREATE)
_EDIT = AuthControl(codes.COLLABORATION_EDIT)
_DELETE = AuthControl(codes.COLLABORATION_DELETE)


# ---------------------------------------------------------------- 工作区
@router.get("/workspace", response_model=ResponseModel, summary="我的工作区")
async def list_my_workspaces(db: DBSession, current: CurrentUser, _perm=_VIEW) -> dict:
    return resp.success(await workspace_service.list_my_workspaces(db, current.id))


@router.post("/workspace", response_model=ResponseModel, summary="新建工作区")
async def create_workspace(
    payload: WorkspaceCreate, db: DBSession, current: CurrentUser, _perm=_CREATE
) -> dict:
    return resp.success(
        await workspace_service.create(db, payload, owner_id=current.id), msg="已创建"
    )


@router.get("/workspace/by-slug/{slug}", response_model=ResponseModel, summary="按 slug 取工作区")
async def get_workspace_by_slug(
    slug: str, db: DBSession, current: CurrentUser, _perm=_VIEW
) -> dict:
    return resp.success(await workspace_service.get_by_slug(db, slug, current.id))


@router.get("/workspace/{workspace_id}", response_model=ResponseModel, summary="工作区详情")
async def get_workspace(
    workspace_id: int, db: DBSession, current: CurrentUser, _perm=_VIEW
) -> dict:
    return resp.success(await workspace_service.get_detail(db, workspace_id, current.id))


@router.put("/workspace/{workspace_id}", response_model=ResponseModel, summary="更新工作区")
async def update_workspace(
    workspace_id: int, payload: WorkspaceUpdate, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    return resp.success(
        await workspace_service.update(db, workspace_id, payload, current.id), msg="已保存"
    )


@router.delete("/workspace/{workspace_id}", response_model=ResponseModel, summary="删除工作区")
async def delete_workspace(
    workspace_id: int, db: DBSession, current: CurrentUser, _perm=_DELETE
) -> dict:
    await workspace_service.delete(db, workspace_id, current.id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 成员
@router.get("/workspace/{workspace_id}/member", response_model=ResponseModel, summary="成员列表")
async def list_members(
    workspace_id: int, db: DBSession, current: CurrentUser, _perm=_VIEW
) -> dict:
    return resp.success(await workspace_service.list_members(db, workspace_id, current.id))


@router.post("/workspace/{workspace_id}/member", response_model=ResponseModel, summary="添加成员")
async def add_member(
    workspace_id: int, payload: MemberAdd, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    return resp.success(
        await workspace_service.add_member(db, workspace_id, payload, current.id), msg="已添加"
    )


@router.put(
    "/workspace/{workspace_id}/member/{member_user_id}",
    response_model=ResponseModel,
    summary="修改成员角色",
)
async def update_member_role(
    workspace_id: int,
    member_user_id: int,
    payload: MemberRoleUpdate,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
) -> dict:
    return resp.success(
        await workspace_service.update_member_role(
            db, workspace_id, member_user_id, payload, current.id
        ),
        msg="已保存",
    )


@router.delete(
    "/workspace/{workspace_id}/member/{member_user_id}",
    response_model=ResponseModel,
    summary="移除成员",
)
async def remove_member(
    workspace_id: int, member_user_id: int, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    await workspace_service.remove_member(db, workspace_id, member_user_id, current.id)
    return resp.success(None, msg="已移除")


# ---------------------------------------------------------------- 任务
@router.get("/workspace/{workspace_id}/task", response_model=ResponseModel, summary="任务列表")
async def list_tasks(
    workspace_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    status: Optional[str] = Query(default=None),
    assigned_to: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await task_service.list_tasks(
        db,
        workspace_id,
        current.id,
        status=status,
        assigned_to=assigned_to,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/workspace/{workspace_id}/task", response_model=ResponseModel, summary="新建任务")
async def create_task(
    workspace_id: int, payload: TaskCreate, db: DBSession, current: CurrentUser, _perm=_CREATE
) -> dict:
    return resp.success(
        await task_service.create_task(db, workspace_id, payload, current.id), msg="已创建"
    )


@router.put("/task/{task_id}", response_model=ResponseModel, summary="更新任务")
async def update_task(
    task_id: int, payload: TaskUpdate, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    """改任务状态 / 内容（**editor 及以上**，且必须先确认属于该工作区 —— 修 v2 的越权入口）"""
    return resp.success(
        await task_service.update_task(db, task_id, payload, current.id), msg="已保存"
    )


@router.delete("/task/{task_id}", response_model=ResponseModel, summary="删除任务")
async def delete_task(
    task_id: int, db: DBSession, current: CurrentUser, _perm=_DELETE
) -> dict:
    await task_service.delete_task(db, task_id, current.id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 团队评论
@router.get("/comment", response_model=ResponseModel, summary="按内容查评论")
async def list_comments(
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
    content_type: str = Query(description="内容类型，如 article / page"),
    content_id: int = Query(description="内容 ID"),
    include_resolved: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    items, total = await comment_service.list_comments(
        db,
        content_type,
        content_id,
        include_resolved=include_resolved,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/comment/mentions", response_model=ResponseModel, summary="@ 到我的评论")
async def list_mentions(
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    limit: int = Query(default=20, ge=1, le=200),
    unread_only: bool = Query(default=False),
) -> dict:
    return resp.success(
        await comment_service.list_mentions(
            db, current.id, limit=limit, unread_only=unread_only
        )
    )


@router.get("/comment/statistics", response_model=ResponseModel, summary="评论统计")
async def comment_statistics(
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
    content_type: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(await comment_service.statistics(db, content_type))


@router.post("/comment", response_model=ResponseModel, summary="发表评论")
async def create_comment(
    payload: CommentCreate, db: DBSession, current: CurrentUser, _perm=_CREATE
) -> dict:
    """补上 v2 **未挂载**的评论入口（v2 的 ``POST /comment`` 没有 ``@router`` 装饰器）"""
    return resp.success(
        await comment_service.create(db, payload, author_id=current.id), msg="已发表"
    )


@router.put("/comment/{comment_id}", response_model=ResponseModel, summary="修改评论")
async def update_comment(
    comment_id: int, payload: CommentUpdate, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    return resp.success(
        await comment_service.update(db, comment_id, payload, current.id), msg="已保存"
    )


@router.delete("/comment/{comment_id}", response_model=ResponseModel, summary="删除评论")
async def delete_comment(
    comment_id: int, db: DBSession, current: CurrentUser, _perm=_DELETE
) -> dict:
    deleted = await comment_service.delete(
        db, comment_id, current.id, is_admin=bool(getattr(current, "is_superuser", False))
    )
    return resp.success({"deleted": deleted}, msg="已删除")


@router.post("/comment/{comment_id}/resolve", response_model=ResponseModel, summary="标记评论已解决")
async def resolve_comment(
    comment_id: int, db: DBSession, current: CurrentUser, _perm=_EDIT
) -> dict:
    """v2 的 resolve **完全没有权限校验**；这里要求作者或管理员"""
    return resp.success(
        await comment_service.resolve(
            db, comment_id, current.id, is_admin=bool(getattr(current, "is_superuser", False))
        ),
        msg="已标记",
    )


# ---------------------------------------------------------------- 协作邀请
@router.get("/invite", response_model=ResponseModel, summary="邀请列表")
async def list_invites(
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
    target_type: Optional[str] = Query(default=None),
    target_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await invite_service.list_invites(
        db, target_type=target_type, target_id=target_id, page=page, page_size=page_size
    )
    return resp.success_page(items, total, page, page_size)


@router.post("/invite", response_model=ResponseModel, summary="新建邀请")
async def create_invite(
    payload: InviteCreate, db: DBSession, current: CurrentUser, _perm=_CREATE
) -> dict:
    return resp.success(
        await invite_service.create(
            db, payload, current.id, is_admin=bool(getattr(current, "is_superuser", False))
        ),
        msg="已创建",
    )


@router.post("/invite/accept", response_model=ResponseModel, summary="接受邀请")
async def accept_invite(
    payload: InviteAcceptRequest, db: DBSession, current: CurrentUser, _perm=_CREATE
) -> dict:
    """接受邀请：工作区邀请会**真实写入成员关系**（v2 只改内存里的计数）"""
    return resp.success(
        await invite_service.accept(db, payload.invite_code, current.id), msg="已加入"
    )


@router.get("/invite/{invite_id}", response_model=ResponseModel, summary="邀请详情")
async def get_invite(
    invite_id: int, db: DBSession, _current: CurrentUser, _perm=_VIEW
) -> dict:
    return resp.success(await invite_service.get_invite(db, invite_id))


@router.delete("/invite/{invite_id}", response_model=ResponseModel, summary="撤销邀请")
async def revoke_invite(
    invite_id: int, db: DBSession, current: CurrentUser, _perm=_DELETE
) -> dict:
    await invite_service.revoke(
        db, invite_id, current.id, is_admin=bool(getattr(current, "is_superuser", False))
    )
    return resp.success(None, msg="已撤销")


# ---------------------------------------------------------------- yjs 协同（HTTP 部分）
@router.get("/yjs/rooms", response_model=ResponseModel, summary="本进程活跃协同房间")
async def list_rooms(
    _current: CurrentUser,
    _perm=_VIEW,
) -> dict:
    """只反映**当前进程**的房间（跨 worker 的房间状态在 Redis 里，不在这里枚举）"""
    rooms = room_registry.snapshot()
    return resp.success({"rooms": rooms, "count": len(rooms)})


@router.post("/yjs/document/{document_id}/save", response_model=ResponseModel, summary="保存协同文档")
async def save_document(
    document_id: int,
    payload: DocumentSaveRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
    invite: Optional[str] = Query(default=None, description="文章协作邀请码（非作者时需要）"),
) -> dict:
    """把前端上报的 HTML 快照落库 + 记一条修订

    CRDT 二进制状态由房间自己写 Redis（见 ``yjs_service``），这里只处理**可读正文**。
    """
    await invite_service.require_document_access(db, document_id, current.id, invite)
    now = datetime.now()
    content_row = (
        await db.execute(
            select(ArticleContent).where(ArticleContent.article == document_id)
        )
    ).scalars().first()
    if content_row is None:
        db.add(ArticleContent(article=document_id, content=payload.html, created_at=now, updated_at=now))
    else:
        content_row.content = payload.html
        content_row.updated_at = now
    # 修订号 = 现有最大 + 1
    last_number = (
                      await db.execute(
                          select(ArticleRevision.revision_number)
                          .where(ArticleRevision.article_id == document_id)
                          .order_by(ArticleRevision.revision_number.desc())
                          .limit(1)
                      )
                  ).scalar() or 0
    db.add(
        ArticleRevision(
            article_id=document_id,
            revision_number=int(last_number) + 1,
            author_id=current.id,
            content=payload.html,
            change_summary=payload.change_summary or "协同编辑保存",
            created_at=now,
        )
    )
    await db.commit()
    return resp.success(
        {"document_id": document_id, "revision_number": int(last_number) + 1}, msg="已保存"
    )


# ---------------------------------------------------------------- yjs 协同（WebSocket）
def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """Cookie → 子协议 ``bearer.<token>`` → query ``token``（三级回退）

    浏览器 WebSocket API 不能自定义请求头，所以 header 方案不可行；
    query 会进访问日志，因此排最后。
    """
    token = websocket.cookies.get("access_token") or websocket.cookies.get("access_token_cookie")
    if token:
        return token
    protocols = websocket.headers.get("sec-websocket-protocol") or ""
    for item in (part.strip() for part in protocols.split(",")):
        if item.startswith("bearer."):
            return item[len("bearer."):]
    return websocket.query_params.get("token")


async def _resolve_ws_user(db: AsyncSession, websocket: WebSocket) -> Optional[User]:
    """解析 WS 连接的身份；任何一步失败都返回 None（调用方据此关闭连接）"""
    token = _extract_ws_token(websocket)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except UnauthorizedError:
        return None
    subject = str(payload.get("sub") or "")
    if not subject:
        return None
    user: Optional[User] = None
    if subject.isdigit():
        user = await db.get(User, int(subject))
    if user is None:
        user = (
            await db.execute(select(User).where(User.username == subject))
        ).scalars().first()
    if user is None or not bool(getattr(user, "is_active", True)):
        return None
    return user


def _with_sync_prefix(frame: bytes) -> bytes:
    """``create_sync_message`` 可能已带 ``YMessageType`` 前缀，这里自适应补全"""
    if frame and frame[0] == int(YMessageType.SYNC):
        return frame
    return bytes([int(YMessageType.SYNC)]) + frame


@router.websocket("/yjs/ws/{document_id}")
async def yjs_websocket(websocket: WebSocket, document_id: int, db: DBSession) -> None:
    """协同编辑通道（y-protocols：sync + awareness）

    与 v2 的差别：**鉴权失败直接 4401 关闭**（v2 是匿名放行），且文档归属由
    ``require_document_access`` 把关（作者本人，或持有指向该文档的有效邀请码）。
    """
    user = await _resolve_ws_user(db, websocket)
    if user is None:
        # 未握手就关闭：客户端拿到 HTTP 403，不会误以为"连上了"
        await websocket.close(code=4401)
        return
    try:
        await invite_service.require_document_access(
            db, document_id, user.id, websocket.query_params.get("invite")
        )
    except Exception as exc:  # noqa: BLE001 - 准入失败一律关闭
        logger.info("yjs 准入被拒: user=%s document=%s reason=%s", user.id, document_id, exc)
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await room_registry.start()
    room = await room_registry.room(document_id)
    client_id = uuid.uuid4().hex[:12]
    room.add(client_id, websocket)
    try:
        # 主动发 sync step1（状态向量），客户端据此回 step2 —— 这是标准 y-protocols 的握手方向
        await websocket.send_bytes(_with_sync_prefix(create_sync_message(room.doc)))
        while True:
            raw = await websocket.receive_bytes()
            if not raw:
                continue
            message_type = raw[0]
            if message_type == int(YMessageType.SYNC):
                reply = handle_sync_message(raw[1:], room.doc)
                if reply:
                    await websocket.send_bytes(_with_sync_prefix(reply))
                    await room_registry.persist_state(room)
            elif message_type == int(YMessageType.AWARENESS):
                room.awareness.apply_awareness_update(raw[1:])
            else:
                continue
            # 同一帧广播给房间内其它人（本地扇出 + 跨 worker）
            await room_registry.broadcast(room, raw, exclude=client_id)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - 单连接异常不应影响房间
        logger.exception("yjs 连接异常: document=%s client=%s", document_id, client_id)
    finally:
        room.remove(client_id)
        if room.empty:
            await room_registry.release(room)
