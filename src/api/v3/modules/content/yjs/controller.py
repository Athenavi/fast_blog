"""yjs 模块路由（content 域：协同编辑文档的持久化面与访问面）

::

    GET  /api/v3/content/yjs/rooms                                             本进程活跃协同房间（需 collaboration:view）
    GET  /api/v3/content/yjs/rooms/{document_id}                               单房间详情 + 版本统计（需 collaboration:view + 文档准入）
    GET  /api/v3/content/yjs/document/{document_id}/access                     我的协同访问权（需 collaboration:view）
    GET  /api/v3/content/yjs/document/{document_id}/collaborators              协作者：作者 + 有效协作邀请（需 collaboration:view + 文档准入）
    GET  /api/v3/content/yjs/document/{document_id}/versions                   版本历史（分页，需 collaboration:view + 文档准入）
    GET  /api/v3/content/yjs/document/{document_id}/version/{revision_number}  版本详情（含正文，需 collaboration:view + 文档准入）
    POST /api/v3/content/yjs/document/{document_id}/snapshot                   保存正文快照（幂等去重，需 collaboration:edit + 写准入）
    POST /api/v3/content/yjs/document/{document_id}/version/{revision_number}/restore  回滚到历史版本（需 collaboration:edit + 写准入）

权限码复用 ``module_content:collaboration:{view,edit}``（``codes.COLLABORATION_*``）：
``codes.py`` 里**没有**独立的 ``yjs`` 权限码，协同编辑本就属于 content 协作能力，因此与
``content/collaboration`` 共用同一组码 —— 不新造码（新码要同时改 ``codes.py`` 与
``seed_rbac.py``，而本任务的写入范围不允许改它们）。

**两层把关**：权限码决定"能不能调用这类管理端点"，**文档准入**决定"能不能碰这份文档"
（作者本人，或持指向该文档的有效协作邀请码；写操作额外要求邀请码 ``permission='edit'``）。
文档不存在 → 404；准入失败 → 403。管理员的权限码**不**自动穿透到别人的私密草稿。

**实时通道不在这里**：WebSocket（y-protocols sync/awareness + Redis 跨进程广播）由同域
``content/collaboration`` 的 ``/api/v3/content/collaboration/yjs/ws/{document_id}`` 提供。
本模块刻意**不实现第二套房间注册表** —— 两个注册表会让同一文档的房间状态分裂，比"少一个
URL"严重得多（详见 ``service.py`` 模块注释）。本模块与那份实现共用**同一个**
``room_registry`` 只读快照，因此这里的房间视图与 WS 房间是同一份事实。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.yjs.schema import RestoreRequest, SnapshotRequest
from src.api.v3.modules.content.yjs.service import yjs_document_service

router = APIRouter(prefix="/yjs", tags=["content-yjs"], route_class=OperationLogRoute)

_VIEW = AuthControl(codes.COLLABORATION_VIEW)
_EDIT = AuthControl(codes.COLLABORATION_EDIT)


# ---------------------------------------------------------------- 房间（进程内只读视图）
@router.get("/rooms", response_model=ResponseModel, summary="本进程活跃协同房间")
async def list_rooms(_current: CurrentUser, _perm=_VIEW) -> dict:
    """进程内运行时状态：只反映**当前进程**的房间，且只有连接数

    跨 worker 的房间状态在 Redis（``content/collaboration`` 的 yjs_service）；该注册表
    **不记录用户身份**（既有实现的既定事实），所以"在线用户"如实降级为"在线连接数"。
    """
    return resp.success(await yjs_document_service.rooms())


@router.get("/rooms/{document_id}", response_model=ResponseModel, summary="单房间详情 + 版本统计")
async def room_detail(
    document_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    invite: Optional[str] = Query(
        default=None,
        description="文章协作邀请码（非作者时需要；持 view 码只能读，持 edit 码才能写）",
    ),
) -> dict:
    """连接数来自进程内注册表，版本统计与正文字符数来自**真表**（``article_revisions`` /
    ``article_content``）——两类数据在同一个返回体里**分别标注口径**。"""
    return resp.success(
        await yjs_document_service.room_detail(
            db, document_id, current.id, invite_code=invite
        )
    )


# ---------------------------------------------------------------- 访问权 / 协作者
@router.get(
    "/document/{document_id}/access",
    response_model=ResponseModel,
    summary="我的协同访问权",
)
async def document_access(
    document_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    invite: Optional[str] = Query(default=None, description="文章协作邀请码（非作者时需要）"),
) -> dict:
    """结构化返回（**不抛 403**）：``allowed`` / ``can_edit`` / 判定依据

    这是"自检"端点（前端据此决定是否显示编辑器、是否只读），因此无权限时返回
    ``allowed=false`` 而不是 403；文档不存在仍按 404。
    """
    return resp.success(
        await yjs_document_service.access(
            db, document_id, current.id, invite_code=invite
        )
    )


@router.get(
    "/document/{document_id}/collaborators",
    response_model=ResponseModel,
    summary="协作者（作者 + 有效协作邀请）",
)
async def document_collaborators(
    document_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    invite: Optional[str] = Query(default=None, description="文章协作邀请码（非作者时需要）"),
) -> dict:
    """v2 的"成员"只在内存里（``clients`` = 连接）；这里来自真表 ``collaboration_invites``

    ``invite_code`` 只对文档作者回显（拿到码就等于能进文档）。
    """
    return resp.success(
        await yjs_document_service.collaborators(
            db, document_id, current.id, invite_code=invite
        )
    )


# ---------------------------------------------------------------- 版本历史
@router.get(
    "/document/{document_id}/versions",
    response_model=ResponseModel,
    summary="版本历史（分页）",
)
async def list_versions(
    document_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    invite: Optional[str] = Query(default=None, description="文章协作邀请码（非作者时需要）"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """真表 ``article_revisions`` 分页（不含正文）；v2 只写版本、从不提供读入口"""
    items, total = await yjs_document_service.versions(
        db,
        document_id,
        current.id,
        invite_code=invite,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.get(
    "/document/{document_id}/version/{revision_number}",
    response_model=ResponseModel,
    summary="版本详情（含正文）",
)
async def version_detail(
    document_id: int,
    revision_number: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    invite: Optional[str] = Query(default=None, description="文章协作邀请码（非作者时需要）"),
) -> dict:
    """返回该版本**完整正文**（超过 20 万字符时截断并置 ``content_is_truncated=true``）"""
    return resp.success(
        await yjs_document_service.version_detail(
            db, document_id, revision_number, current.id, invite_code=invite
        )
    )


# ---------------------------------------------------------------- 写：快照 / 回滚
@router.post(
    "/document/{document_id}/snapshot",
    response_model=ResponseModel,
    summary="保存协同正文快照",
)
async def save_snapshot(
    document_id: int,
    payload: SnapshotRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
    invite: Optional[str] = Query(
        default=None, description="协作邀请码（非作者时必须持 permission=edit 的码）"
    ),
) -> dict:
    """更新 ``article_content`` + **追加**一条 ``article_revisions``（同一事务）

    正文与最新修订一致时**跳过写入**并返回 ``saved=false``（避免自动保存堆满重复修订；
    ``force=true`` 可强制）；正文完整入库 —— 不像 v2 那样截断到 500 字符。
    """
    result = await yjs_document_service.snapshot(
        db, document_id, payload, current.id, invite_code=invite
    )
    return resp.success(result, msg="已保存" if result.get("saved") else "内容未变化")


@router.post(
    "/document/{document_id}/version/{revision_number}/restore",
    response_model=ResponseModel,
    summary="回滚到历史版本",
)
async def restore_version(
    document_id: int,
    revision_number: int,
    payload: RestoreRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
    invite: Optional[str] = Query(
        default=None, description="协作邀请码（非作者时必须持 permission=edit 的码）"
    ),
) -> dict:
    """把历史版本正文写回 ``article_content`` 并**追加**一条新修订（历史不被改写）"""
    return resp.success(
        await yjs_document_service.restore(
            db,
            document_id,
            revision_number,
            payload,
            current.id,
            invite_code=invite,
        ),
        msg="已回滚",
    )
