"""comment 模块路由

**公开（无鉴权）**::

    GET  /api/v3/content/comment/public/article/{article_id}  某文章的公开评论树
    POST /api/v3/content/comment/public                       提交评论（登录或访客）

**管理端（需权限码）**::

    GET    /api/v3/content/comment                  评论列表
    GET    /api/v3/content/comment/pending          待审核评论
    POST   /api/v3/content/comment/batch/delete     批量删除
    GET    /api/v3/content/comment/{comment_id}     评论详情（含隐私字段）
    PUT    /api/v3/content/comment/{comment_id}     编辑评论内容
    DELETE /api/v3/content/comment/{comment_id}     删除评论（级联回复）
    POST   /api/v3/content/comment/{comment_id}/approve  通过审核
    POST   /api/v3/content/comment/{comment_id}/reject   拒绝审核

``/pending``、``/batch/delete`` 是静态路径，必须注册在 ``/{comment_id}`` 之前。

权限码：``comment:view`` / ``comment:approve`` / ``comment:edit`` / ``comment:delete``。
公开提交走可选登录（``jwt_optional_dependency``），未登录即访客评论。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.comment.schema import (
    CommentBatchDecideRequest,
    CommentBatchDeleteRequest,
    CommentCreate,
    CommentReplyRequest,
    CommentUpdate,
)
from src.api.v3.modules.content.comment.service import comment_service
from src.auth.auth_deps import jwt_optional_dependency

router = APIRouter(prefix="/comment", tags=["content-comment"], route_class=OperationLogRoute)


# ─────────────────────────── 公开读 / 公开提交 ───────────────────────────
@router.get(
    "/public/article/{article_id}",
    response_model=ResponseModel,
    summary="文章公开评论树（无需鉴权）",
)
async def public_article_comments(
    article_id: int,
    db: DBSession,
    approved_only: bool = Query(default=True, description="仅返回已审核通过"),
) -> dict:
    return resp.success(await comment_service.article_tree(db, article_id, approved_only=approved_only))


@router.post("/public", response_model=ResponseModel, summary="提交评论（无需鉴权）")
async def submit_comment(
    payload: CommentCreate,
    request: Request,
    db: DBSession,
    user=Depends(jwt_optional_dependency),
) -> dict:
    data = await comment_service.create_comment(
        db,
        payload,
        user=user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return resp.success(data, msg="评论已提交")


# ─────────────────────────── 管理端：静态路径优先 ───────────────────────────
@router.get("/pending", response_model=ResponseModel, summary="待审核评论")
async def pending_comments(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_VIEW),
) -> dict:
    items, total = await comment_service.list_pending(
        db, page=page.page, page_size=page.page_size, scope_user=_current
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除评论")
async def batch_delete_comments(
    payload: CommentBatchDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_DELETE),
) -> dict:
    affected = await comment_service.batch_delete(db, payload.ids)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 条")


@router.post("/batch/decide", response_model=ResponseModel, summary="批量通过 / 拒绝评论")
async def batch_decide_comments(
    payload: CommentBatchDecideRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_APPROVE),
) -> dict:
    affected = await comment_service.batch_set_approved(db, payload.ids, payload.approve)
    action = "通过" if payload.approve else "拒绝"
    return resp.success({"affected": affected}, msg=f"已{action} {affected} 条")


# ─────────────────────────── 管理端：列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="评论列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 评论列表",
)
async def list_comments(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_VIEW),
    article_id: Optional[int] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    is_approved: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await comment_service.list_comments(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        article_id=article_id,
        user_id=user_id,
        is_approved=is_approved,
        order_by=page.order_by,
        order=page.order,
        scope_user=_current,
    )
    return resp.success_page(items, total, page.page, page.page_size)


# ─────────────────────────── 管理端：详情 / 编辑 / 删除 / 审核 ───────────────────────────
@router.get("/{comment_id}", response_model=ResponseModel, summary="评论详情")
async def get_comment(
    comment_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_VIEW),
) -> dict:
    return resp.success(await comment_service.get_comment(db, comment_id, scope_user=_current))


@router.put("/{comment_id}", response_model=ResponseModel, summary="编辑评论")
async def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_EDIT),
) -> dict:
    return resp.success(await comment_service.update_comment(db, comment_id, payload.content), msg="更新成功")


@router.delete("/{comment_id}", response_model=ResponseModel, summary="删除评论")
async def delete_comment(
    comment_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_DELETE),
) -> dict:
    await comment_service.delete_comment(db, comment_id)
    return resp.success(None, msg="已删除")


@router.post("/{comment_id}/like", response_model=ResponseModel, summary="点赞 / 取消点赞")
async def like_comment(
    comment_id: int,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    data = await comment_service.toggle_like(db, comment_id=comment_id, user_id=current.id)
    return resp.success(data, msg="已点赞" if data["liked"] else "已取消点赞")


@router.post("/{comment_id}/reply", response_model=ResponseModel, summary="管理员回复评论")
async def reply_comment(
    comment_id: int,
    payload: CommentReplyRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_EDIT),
) -> dict:
    data = await comment_service.reply_comment(db, comment_id, payload.content, user=current)
    return resp.success(data, msg="回复已发布")


@router.post("/{comment_id}/approve", response_model=ResponseModel, summary="通过审核")
async def approve_comment(
    comment_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_APPROVE),
) -> dict:
    return resp.success(await comment_service.set_approved(db, comment_id, True), msg="已通过")


@router.post("/{comment_id}/reject", response_model=ResponseModel, summary="拒绝审核")
async def reject_comment(
    comment_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.COMMENT_APPROVE),
) -> dict:
    return resp.success(await comment_service.set_approved(db, comment_id, False), msg="已拒绝")
