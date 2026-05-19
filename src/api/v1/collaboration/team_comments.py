"""
团队评论和反馈 API

提供团队内部评论的管理功能
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body

from src.api.v1.core.responses import ApiResponse
from shared.services.comments.team_comments import team_comment_service
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/comment", summary="创建评论", description="创建团队评论")
async def create_comment(
        content_id: int = Body(..., description="内容ID"),
        content_type: str = Body(..., description="内容类型"),
        text: str = Body(..., description="评论内容"),
        parent_id: Optional[int] = Body(None, description="父评论ID（回复）"),
        mentions: Optional[List[int]] = Body(None, description="@提及的用户ID列表"),
        current_user=Depends(jwt_required),
):
    """创建评论"""
    comment = team_comment_service.create_comment(
        content_id=content_id,
        content_type=content_type,
        author_id=current_user.id,
        author_name=getattr(current_user, 'username', 'Unknown'),
        text=text,
        parent_id=parent_id,
        mentions=mentions,
    )

    return ApiResponse(
        success=True,
        message="Comment created",
        data=comment
    )


@router.put("/comment/{comment_id}", summary="更新评论", description="更新评论内容")
async def update_comment(
        comment_id: int,
        text: str = Body(..., description="新的评论内容"),
        current_user=Depends(jwt_required),
):
    """更新评论"""
    try:
        comment = team_comment_service.update_comment(
            comment_id=comment_id,
            author_id=current_user.id,
            text=text,
        )

        return ApiResponse(
            success=True,
            message="Comment updated",
            data=comment
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/comment/{comment_id}", summary="删除评论", description="删除评论")
async def delete_comment(
        comment_id: int,
        current_user=Depends(jwt_required),
):
    """删除评论"""
    try:
        is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)

        success = team_comment_service.delete_comment(
            comment_id=comment_id,
            user_id=current_user.id,
            is_admin=is_admin,
        )

        if success:
            return ApiResponse(
                success=True,
                message="Comment deleted"
            )
        else:
            return ApiResponse(
                success=False,
                error="Comment not found"
            )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/comment/{comment_id}/resolve", summary="标记为已解决", description="标记评论为已解决")
async def resolve_comment(
        comment_id: int,
        current_user=Depends(jwt_required),
):
    """标记为已解决"""
    try:
        comment = team_comment_service.resolve_comment(
            comment_id=comment_id,
            resolver_id=current_user.id,
            resolver_name=getattr(current_user, 'username', 'Unknown'),
        )

        return ApiResponse(
            success=True,
            message="Comment resolved",
            data=comment
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/content/{content_type}/{content_id}", summary="获取内容评论", description="获取指定内容的评论")
async def get_content_comments(
        content_type: str,
        content_id: int,
        include_resolved: bool = Query(True, description="是否包含已解决的评论"),
        current_user=Depends(jwt_required),
):
    """获取内容评论"""
    comments = team_comment_service.get_comments_for_content(
        content_id=content_id,
        content_type=content_type,
        include_resolved=include_resolved,
    )

    return ApiResponse(
        success=True,
        data={
            'comments': comments,
            'count': len(comments),
        }
    )


@router.get("/mentions", summary="获取@提及", description="获取@当前用户的评论")
async def get_mentions(
        unread_only: bool = Query(False, description="是否只返回未读的"),
        current_user=Depends(jwt_required),
):
    """获取@提及"""
    mentions = team_comment_service.get_user_mentions(
        user_id=current_user.id,
        unread_only=unread_only,
    )

    return ApiResponse(
        success=True,
        data={
            'mentions': mentions,
            'count': len(mentions),
        }
    )


@router.get("/statistics", summary="获取统计信息", description="获取评论统计信息")
async def get_statistics(
        content_id: Optional[int] = Query(None, description="内容ID过滤"),
        content_type: Optional[str] = Query(None, description="内容类型过滤"),
        current_user=Depends(jwt_required),
):
    """获取统计信息"""
    stats = team_comment_service.get_statistics(
        content_id=content_id,
        content_type=content_type,
    )

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/examples", summary="使用示例", description="获取团队评论使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "workflow": {
            'description': '团队协作流程',
            'steps': [
                '1. 团队成员查看内容并添加评论',
                '2. 使用@提及通知相关人员',
                '3. 通过回复进行线程讨论',
                '4. 问题解决后标记为已解决',
                '5. 定期查看统计了解协作情况',
            ]
        },
        "mention_syntax": {
            'description': '@提及使用',
            'example': '''
# 在评论内容中使用 @user_id 格式
POST /api/v1/team-comments/comment
{
  "content_id": 123,
  "content_type": "article",
  "text": "@2 @3 请审核这篇文章的内容准确性",
  "mentions": [2, 3]  // 同时传入用户ID列表
}

# 被提及的用户会收到通知
GET /api/v1/team-comments/mentions
            '''.strip()
        },
        "thread_discussion": {
            'description': '线程讨论',
            'example': '''
# 创建主评论
POST /api/v1/team-comments/comment
{
  "content_id": 123,
  "content_type": "article",
  "text": "这个章节需要补充更多案例"
}
// 返回: {"id": 1, ...}

# 回复该评论
POST /api/v1/team-comments/comment
{
  "content_id": 123,
  "content_type": "article",
  "text": "我同意，我来补充几个实际案例",
  "parent_id": 1  // 回复评论1
}

# 继续回复
POST /api/v1/team-comments/comment
{
  "content_id": 123,
  "content_type": "article",
  "text": "已经补充完成，请查看",
  "parent_id": 1
}

# 标记为已解决
POST /api/v1/team-comments/comment/1/resolve
            '''.strip()
        },
        "integration_tips": {
            'description': '集成建议',
            'tips': [
                '在文章编辑页面侧边栏显示评论',
                '实时通知被@的用户',
                '支持Markdown格式的评论内容',
                '提供评论搜索和过滤功能',
                '在仪表板显示未解决的评论数',
                '定期清理已解决的旧评论',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
