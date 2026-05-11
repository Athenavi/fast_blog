"""
内容审批工作流 API

提供内容审批的管理功能
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from shared.services.content_approval import approval_workflow
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.post("/submit", summary="提交审批", description="提交内容进行审批")
async def submit_for_approval(
        content_id: int = Body(..., description="内容ID"),
        content_type: str = Body(..., description="内容类型 (article, page)"),
        title: str = Body(..., description="标题"),
        reviewers: Optional[List[int]] = Body(None, description="审核人ID列表"),
        current_user=Depends(jwt_required),
):
    """提交审批"""
    result = approval_workflow.submit_for_approval(
        content_id=content_id,
        content_type=content_type,
        author_id=current_user.id,
        author_name=getattr(current_user, 'username', 'Unknown'),
        title=title,
        reviewers=reviewers,
    )

    return ApiResponse(
        success=True,
        message="Content submitted for approval",
        data=result
    )


@router.post("/start-review/{content_id}", summary="开始审核", description="开始审核内容")
async def start_review(
        content_id: int,
        current_user=Depends(jwt_required),
):
    """开始审核"""
    try:
        result = approval_workflow.start_review(
            content_id=content_id,
            reviewer_id=current_user.id,
            reviewer_name=getattr(current_user, 'username', 'Unknown'),
        )

        return ApiResponse(
            success=True,
            message="Review started",
            data=result
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/approve/{content_id}", summary="批准内容", description="批准内容")
async def approve_content(
        content_id: int,
        comment: Optional[str] = Body(None, description="审批意见"),
        current_user=Depends(jwt_required),
):
    """批准内容"""
    try:
        result = approval_workflow.approve_content(
            content_id=content_id,
            reviewer_id=current_user.id,
            reviewer_name=getattr(current_user, 'username', 'Unknown'),
            comment=comment,
        )

        return ApiResponse(
            success=True,
            message="Content approved",
            data=result
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/reject/{content_id}", summary="拒绝内容", description="拒绝内容")
async def reject_content(
        content_id: int,
        reason: str = Body(..., description="拒绝原因"),
        current_user=Depends(jwt_required),
):
    """拒绝内容"""
    try:
        result = approval_workflow.reject_content(
            content_id=content_id,
            reviewer_id=current_user.id,
            reviewer_name=getattr(current_user, 'username', 'Unknown'),
            reason=reason,
        )

        return ApiResponse(
            success=True,
            message="Content rejected",
            data=result
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/publish/{content_id}", summary="发布内容", description="发布已批准的内容")
async def publish_content(
        content_id: int,
        current_user=Depends(jwt_required),
):
    """发布内容"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        result = approval_workflow.publish_content(
            content_id=content_id,
            publisher_id=current_user.id,
            publisher_name=getattr(current_user, 'username', 'Unknown'),
        )

        return ApiResponse(
            success=True,
            message="Content published",
            data=result
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/resubmit/{content_id}", summary="重新提交", description="重新提交被拒绝的内容")
async def resubmit_content(
        content_id: int,
        current_user=Depends(jwt_required),
):
    """重新提交"""
    try:
        result = approval_workflow.resubmit_content(
            content_id=content_id,
            author_id=current_user.id,
            author_name=getattr(current_user, 'username', 'Unknown'),
        )

        return ApiResponse(
            success=True,
            message="Content resubmitted",
            data=result
        )
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/status/{content_id}", summary="获取审批状态", description="获取内容的审批状态")
async def get_approval_status(
        content_id: int,
        current_user=Depends(jwt_required),
):
    """获取审批状态"""
    status = approval_workflow.get_approval_status(content_id)

    if not status:
        return ApiResponse(
            success=False,
            error="No approval record found"
        )

    return ApiResponse(
        success=True,
        data=status
    )


@router.get("/pending", summary="获取待审批列表", description="获取待审批的内容列表")
async def get_pending_approvals(
        current_user=Depends(jwt_required),
):
    """获取待审批列表"""
    pending = approval_workflow.get_pending_approvals()

    return ApiResponse(
        success=True,
        data={
            'pending_approvals': pending,
            'count': len(pending),
        }
    )


@router.get("/history/{content_id}", summary="获取审批历史", description="获取内容的审批历史")
async def get_approval_history(
        content_id: int,
        current_user=Depends(jwt_required),
):
    """获取审批历史"""
    history = approval_workflow.get_approval_history(content_id)

    return ApiResponse(
        success=True,
        data={
            'history': history,
            'count': len(history),
        }
    )


@router.get("/statistics", summary="获取统计信息", description="获取审批统计信息")
async def get_statistics(
        hours: int = Query(24, ge=1, le=168, description="统计最近多少小时"),
        current_user=Depends(jwt_required),
):
    """获取统计信息"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    stats = approval_workflow.get_statistics(hours=hours)

    return ApiResponse(
        success=True,
        data=stats
    )


@router.get("/examples", summary="使用示例", description="获取审批工作流使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "workflow": {
            'description': '审批工作流程',
            'steps': [
                '1. 作者创建内容并提交审批 (/submit)',
                '2. 审核人开始审核 (/start-review)',
                '3. 审核人批准或拒绝 (/approve 或 /reject)',
                '4. 如果是多级审批，下一位审核人继续',
                '5. 所有审核人批准后，管理员发布 (/publish)',
                '6. 如果被拒绝，作者修改后重新提交 (/resubmit)',
            ]
        },
        "multi_level_approval": {
            'description': '多级审批配置',
            'example': '''
# 提交时需要指定多个审核人
POST /api/v1/approval/submit
{
  "content_id": 123,
  "content_type": "article",
  "title": "重要文章",
  "reviewers": [2, 3, 4]  // 三位审核人
}

# 审核流程：
# - 审核人2批准 → 等待审核人3
# - 审核人3批准 → 等待审核人4
# - 审核人4批准 → 审批完成，状态变为approved
# - 管理员发布 → 状态变为published
            '''.strip()
        },
        "integration": {
            'description': '与文章系统集成',
            'code_example': '''
from shared.services.content_approval import approval_workflow

# 在文章创建时自动提交审批
@app.post("/articles")
async def create_article(article_data: ArticleCreate):
    article = await save_article(article_data)
    
    # 如果需要审批
    if requires_approval(article_data.category):
        approval_workflow.submit_for_approval(
            content_id=article.id,
            content_type='article',
            author_id=current_user.id,
            author_name=current_user.username,
            title=article.title,
            reviewers=get_reviewers_for_category(article_data.category)
        )
        
        return {"message": "Article submitted for approval"}
    else:
        # 直接发布
        return {"message": "Article published"}
            '''.strip()
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
