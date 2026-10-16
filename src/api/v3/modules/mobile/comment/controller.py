"""mobile/comment：移动端评论列表 / 发表 / 点赞

路由前缀：``/api/v3/mobile/comment``

复用 ``modules/content/comment`` 的 ``comment_service``（同一套隐私过滤：公开读不返回
``author_email`` / ``author_ip`` / ``user_agent``，回复树组装逻辑一致）。

legacy 缺陷修复：旧实现 ``POST /{comment_id}/like`` 引用了**不存在的** ``CommentLike`` 类
（项目里真实模型是 ``CommentVote``），必然 NameError；v3 用 ``toggle_like`` 正确实现。
"""

from fastapi import APIRouter, Depends, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.modules.content.comment.schema import CommentCreate
from src.api.v3.modules.content.comment.service import comment_service
from src.auth.auth_deps import jwt_required_dependency

router = APIRouter(prefix="/comment", tags=["mobile-comment"])


@router.get("/article/{article_id}", response_model=ResponseModel, summary="文章评论树（无需鉴权）")
async def article_comments(article_id: int, db: DBSession) -> dict:
    return resp.success(await comment_service.article_tree(db, article_id, approved_only=True))


@router.post("", response_model=ResponseModel, summary="发表评论（需登录）")
async def create_comment(
    payload: CommentCreate,
    request: Request,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    data = await comment_service.create_comment(
        db,
        payload,
        user=user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return resp.success(data, msg="评论已提交")


@router.post("/{comment_id}/like", response_model=ResponseModel, summary="点赞 / 取消点赞（需登录）")
async def like_comment(
    comment_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    data = await comment_service.toggle_like(db, comment_id=comment_id, user_id=user.id)
    return resp.success(data, msg="已点赞" if data["liked"] else "已取消点赞")
