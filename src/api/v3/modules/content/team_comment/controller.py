"""team_comment 模块路由（content 域：团队 / 内部评论）

::

    GET    /api/v3/content/team_comment                 按内容查评论树
    GET    /api/v3/content/team_comment/mentions        @ 到我的评论
    GET    /api/v3/content/team_comment/statistics      评论统计
    POST   /api/v3/content/team_comment                 发表评论
    GET    /api/v3/content/team_comment/{comment_id}    评论详情
    PUT    /api/v3/content/team_comment/{comment_id}    修改评论
    DELETE /api/v3/content/team_comment/{comment_id}    删除评论（级联子孙）
    POST   /api/v3/content/team_comment/{comment_id}/resolve  标记已解决

``/mentions``、``/statistics`` 是静态路径，必须注册在 ``/{comment_id}`` 之前（否则会被参数路径遮蔽）。

权限码：``module_content:collaboration:{view,create,edit,delete}``（复用既有协作权限码）。
**所有端点都要求登录 + 权限码**（后端强制，不靠前端）；写操作（改造 / 删除 / 解决）在 service 层
额外要求**评论作者或管理员**。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.team_comment.schema import (
    TeamCommentCreate,
    TeamCommentUpdate,
)
from src.api.v3.modules.content.team_comment.service import team_comment_service

router = APIRouter(
    prefix="/team_comment", tags=["content-team-comment"], route_class=OperationLogRoute
)

_VIEW = AuthControl(codes.COLLABORATION_VIEW)
_CREATE = AuthControl(codes.COLLABORATION_CREATE)
_EDIT = AuthControl(codes.COLLABORATION_EDIT)
_DELETE = AuthControl(codes.COLLABORATION_DELETE)


def _is_admin(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


# ---------------------------------------------------------------- 静态路径优先
@router.get("/mentions", response_model=ResponseModel, summary="@ 到我的团队评论")
async def list_my_mentions(
    db: DBSession,
    current: CurrentUser,
    _perm=_VIEW,
    limit: int = Query(default=20, ge=1, le=200),
    unread_only: bool = Query(default=False, description="仅未解决（既有表无独立已读状态）"),
) -> dict:
    """@ 到我的评论（SQL 粗筛 + 应用层精确解析 ``mentions``，不误匹配 ``[11,21]``）"""
    return resp.success(
        await team_comment_service.list_mentions(
            db, current.id, limit=limit, unread_only=unread_only
        )
    )


@router.get("/statistics", response_model=ResponseModel, summary="团队评论统计")
async def comment_statistics(
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
    content_type: Optional[str] = Query(default=None),
    content_id: Optional[int] = Query(default=None),
) -> dict:
    """按内容对象（可选）统计：总数 / 已解决 / 未解决 / 各作者计数"""
    return resp.success(
        await team_comment_service.statistics(
            db, content_type=content_type, content_id=content_id
        )
    )


# ---------------------------------------------------------------- 列表 / 创建
@router.get("", response_model=ResponseModel, summary="按内容查团队评论树")
async def list_team_comments(
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
    content_type: str = Query(description="内容类型，如 article / page"),
    content_id: int = Query(description="内容 ID"),
    include_resolved: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """返回按 ``parent_id`` 组装的评论线程树（顶层评论分页）"""
    items, total = await team_comment_service.list_for_content(
        db,
        content_type,
        content_id,
        include_resolved=include_resolved,
        page=page,
        page_size=page_size,
    )
    return resp.success_page(items, total, page, page_size)


@router.post("", response_model=ResponseModel, summary="发表团队评论")
async def create_team_comment(
    payload: TeamCommentCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=_CREATE,
) -> dict:
    """发表评论：``text`` 入库前 ``html.escape``；父评论须属于同一内容对象"""
    return resp.success(
        await team_comment_service.create(db, payload, author_id=current.id), msg="已发表"
    )


# ---------------------------------------------------------------- 详情 / 写（参数路径，注册在静态路径之后）
@router.get("/{comment_id}", response_model=ResponseModel, summary="团队评论详情")
async def get_team_comment(
    comment_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=_VIEW,
) -> dict:
    """单条评论（``mentions`` 已解析为整数列表，``author_name`` 由 ``author_id`` 补齐）"""
    return resp.success(await team_comment_service.get(db, comment_id))


@router.put("/{comment_id}", response_model=ResponseModel, summary="修改团队评论")
async def update_team_comment(
    comment_id: int,
    payload: TeamCommentUpdate,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
) -> dict:
    """仅**评论作者或管理员**可修改"""
    return resp.success(
        await team_comment_service.update(
            db, comment_id, payload, user_id=current.id, is_admin=_is_admin(current)
        ),
        msg="已保存",
    )


@router.delete("/{comment_id}", response_model=ResponseModel, summary="删除团队评论")
async def delete_team_comment(
    comment_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_DELETE,
) -> dict:
    """仅**评论作者或管理员**可删除；级联删除其全部子孙回复"""
    deleted = await team_comment_service.delete(
        db, comment_id, user_id=current.id, is_admin=_is_admin(current)
    )
    return resp.success({"deleted": deleted}, msg=f"已删除 {deleted} 条")


@router.post("/{comment_id}/resolve", response_model=ResponseModel, summary="标记评论已解决")
async def resolve_team_comment(
    comment_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=_EDIT,
) -> dict:
    """仅**评论作者或管理员**可标记（v2 的 resolve 完全没有权限校验）"""
    return resp.success(
        await team_comment_service.resolve(
            db, comment_id, user_id=current.id, is_admin=_is_admin(current)
        ),
        msg="已标记解决",
    )
