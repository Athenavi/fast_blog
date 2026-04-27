"""
评论管理API - 包含垃圾评论过滤
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment import Comment
from shared.services.comment_manager import comment_like_service, comment_notification_service
from shared.services.spam_filter_manager import spam_filter
from shared.services.user_manager import gravatar_service
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.auth.auth_deps import jwt_optional_dependency
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["comments"])


class CreateCommentRequest(BaseModel):
    """创建评论请求"""
    article_id: int
    content: str
    parent_id: Optional[int] = None  # 回复评论时使用

    # 访客信息（未登录用户必填）
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_url: Optional[str] = None
    
    # 蜜罐字段(前端隐藏,正常用户不会填写)
    website_url: Optional[str] = None
    phone_field: Optional[str] = None
    comment_extra: Optional[str] = None

    # 页面加载时间戳(用于检测快速提交)
    page_load_time: Optional[float] = None


class UpdateCommentRequest(BaseModel):
    """更新评论请求"""
    content: str


@router.post("/comments")
async def create_comment(
        request: Request,
        comment_data: CreateCommentRequest,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_optional_dependency)
):
    """
    创建新评论（支持登录用户和访客）
    
    自动进行垃圾评论检测:
    - 低风险: 直接发布
    - 中风险: 标记为待审核
    - 高风险: 直接拒绝
    """
    try:
        from sqlalchemy import select
        import json

        # 1. 检查文章是否存在
        from shared.models.article import Article
        article_query = select(Article).where(Article.id == comment_data.article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="文章不存在")

        # 2. 获取用户IP和User-Agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")

        # 3. 收集蜜罐字段数据
        honeypot_data = {
            'website_url': comment_data.website_url or '',
            'phone_field': comment_data.phone_field or '',
            'comment_extra': comment_data.comment_extra or ''
        }

        # 4. 执行垃圾评论检测(增强版)
        spam_check = spam_filter.check_spam(
            content=comment_data.content,
            user_id=current_user.id if current_user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            honeypot_data=honeypot_data,
            submit_time=comment_data.page_load_time
        )

        # 5. 根据检测结果决定操作
        if spam_check['action'] == 'reject':
            return ApiResponse(
                success=False,
                error="评论被识别为垃圾内容，已拒绝",
                data={
                    "spam_detected": True,
                    "confidence": spam_check['confidence'],
                    "reasons": spam_check['reasons']
                }
            )

        # 6. 创建评论
        is_approved = spam_check['action'] == 'approve'

        new_comment = Comment(
            article_id=comment_data.article_id,
            user_id=current_user.id if current_user else None,
            parent_id=comment_data.parent_id,
            content=comment_data.content,
            is_approved=is_approved,
            likes=0,
            # 访客信息
            author_name=comment_data.author_name,
            author_email=comment_data.author_email,
            author_url=comment_data.author_url,
            author_ip=ip_address,
            user_agent=user_agent,
            # 垃圾检测信息
            spam_score=spam_check['confidence'],
            spam_reasons=json.dumps(spam_check['reasons']) if spam_check['reasons'] else None
        )

        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)

        # 7. 发送通知(如果评论通过审核)
        if is_approved:
            try:
                from shared.models.article import Article
                from shared.models.user import User
                from urllib.parse import urljoin
                import os

                article_query = select(Article).where(Article.id == comment_data.article_id)
                article_result = await db.execute(article_query)
                article = article_result.scalar_one_or_none()

                # 获取文章作者信息
                if article and article.user:
                    author_query = select(User).where(User.id == article.user)
                    author_result = await db.execute(author_query)
                    article_author = author_result.scalar_one_or_none()

                    if article_author and article_author.email:
                        # 获取评论者信息
                        commenter_name = current_user.username if current_user else comment_data.author_name or '访客'

                        # 构建URL
                        base_url = os.getenv('SITE_URL', 'http://localhost:3000')
                        article_url = urljoin(base_url, f"/articles/detail?id={article.id}")
                        comment_url = urljoin(base_url, f"/articles/detail?id={article.id}#comment-{new_comment.id}")

                        # 通知文章作者
                        comment_notification_service.notify_article_author(
                            author_email=article_author.email,
                            author_name=article_author.username,
                            article_title=article.title,
                            article_url=article_url,
                            commenter_name=commenter_name,
                            comment_content=new_comment.content,
                            comment_url=comment_url,
                            article_id=article.id,
                            author_user_id=article_author.id
                        )

                # 如果有父评论，通知被回复者
                if new_comment.parent_id:
                    parent_query = select(Comment).where(Comment.id == new_comment.parent_id)
                    parent_result = await db.execute(parent_query)
                    parent_comment = parent_result.scalar_one_or_none()

                    if parent_comment and parent_comment.author_email:
                        commenter_name = current_user.username if current_user else comment_data.author_name or '访客'

                        base_url = os.getenv('SITE_URL', 'http://localhost:3000')
                        article_url = urljoin(base_url, f"/articles/detail?id={comment_data.article_id}")
                        comment_url = urljoin(base_url,
                                              f"/articles/detail?id={comment_data.article_id}#comment-{new_comment.id}")

                        # 通知被回复者
                        comment_notification_service.notify_comment_reply(
                            recipient_email=parent_comment.author_email,
                            recipient_name=parent_comment.author_name or '用户',
                            article_title=article.title if article else '文章',
                            article_url=article_url,
                            replier_name=commenter_name,
                            reply_content=new_comment.content,
                            original_comment=parent_comment.content,
                            comment_url=comment_url,
                            article_id=comment_data.article_id,
                            recipient_user_id=parent_comment.user_id
                        )

            except Exception as e:
                print(f"发送评论通知失败: {e}")
                import traceback
                traceback.print_exc()
                # 通知失败不影响评论创建

        # 8. 返回结果
        return ApiResponse(
            success=True,
            data={
                "id": new_comment.id,
                "content": new_comment.content,
                "is_approved": new_comment.is_approved,
                "created_at": new_comment.created_at.isoformat() if new_comment.created_at else None,
                "spam_check": {
                    "action": spam_check['action'],
                    "confidence": spam_check['confidence'],
                    "needs_moderation": not is_approved
                }
            },
            message="评论提交成功" if is_approved else "评论已提交，等待审核"
        )

    except Exception as e:
        await db.rollback()
        import traceback
        print(f"创建评论失败: {e}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"创建评论失败: {str(e)}")


@router.get("/comments/{comment_id}")
async def get_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """获取单条评论详情"""
    try:
        from sqlalchemy import select

        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return ApiResponse(success=False, error="评论不存在")

        return ApiResponse(
            success=True,
            data=comment.to_dict()
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取评论失败: {str(e)}")


@router.get("/articles/{article_id}/comments")
async def get_article_comments(
        article_id: int,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章的所有已审核评论"""
    try:
        from sqlalchemy import select, func
        from shared.models.user import User

        # 查询已审核的评论
        query = (
            select(Comment)
            .where(Comment.article_id == article_id)
            .where(Comment.is_approved == True)
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await db.execute(query)
        comments = result.scalars().all()

        # 统计总数
        count_query = (
            select(func.count(Comment.id))
            .where(Comment.article_id == article_id)
            .where(Comment.is_approved == True)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 为每个评论添加用户信息和头像
        comments_data = []
        for comment in comments:
            comment_dict = comment.to_dict()

            # 获取用户信息
            user_query = select(User).where(User.id == comment.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if user:
                comment_dict['username'] = user.username
                comment_dict['avatar_url'] = gravatar_service.get_avatar_url(
                    email=user.email if hasattr(user, 'email') else '',
                    size=80,
                    default='identicon'
                )
            else:
                comment_dict['username'] = 'Unknown'
                comment_dict['avatar_url'] = gravatar_service.get_avatar_url(
                    email='',
                    size=80,
                    default='mp'
                )

            comments_data.append(comment_dict)

        return ApiResponse(
            success=True,
            data={
                "comments": comments_data,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取评论列表失败: {str(e)}")


@router.put("/comments/{comment_id}")
async def update_comment(
        comment_id: int,
        update_data: UpdateCommentRequest,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """更新评论(仅作者或管理员)"""
    try:
        from sqlalchemy import select

        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return ApiResponse(success=False, error="评论不存在")

        # 检查权限
        if comment.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            return ApiResponse(success=False, error="无权修改此评论")

        # 更新内容
        comment.content = update_data.content
        await db.commit()

        return ApiResponse(
            success=True,
            data=comment.to_dict(),
            message="评论更新成功"
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"更新评论失败: {str(e)}")


@router.delete("/comments/{comment_id}")
async def delete_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """删除评论(仅作者或管理员)"""
    try:
        from sqlalchemy import select

        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return ApiResponse(success=False, error="评论不存在")

        # 检查权限
        if comment.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            return ApiResponse(success=False, error="无权删除此评论")

        await db.delete(comment)
        await db.commit()

        return ApiResponse(
            success=True,
            message="评论删除成功"
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"删除评论失败: {str(e)}")


# ==================== 管理员评论审核API ====================

@router.get("/admin/comments/pending")
async def get_pending_comments(
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """获取待审核的评论(仅管理员)"""
    try:
        from sqlalchemy import select, func

        # 检查是否为管理员
        if not getattr(current_user, 'is_admin', False):
            return ApiResponse(success=False, error="需要管理员权限")

        # 查询待审核评论
        query = (
            select(Comment)
            .where(Comment.is_approved == False)
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await db.execute(query)
        comments = result.scalars().all()

        # 统计总数
        count_query = (
            select(func.count(Comment.id))
            .where(Comment.is_approved == False)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return ApiResponse(
            success=True,
            data={
                "comments": [c.to_dict() for c in comments],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取待审核评论失败: {str(e)}")


@router.post("/admin/comments/{comment_id}/approve")
async def approve_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """审核通过评论(仅管理员)"""
    try:
        from sqlalchemy import select
        from datetime import datetime, timezone

        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return ApiResponse(success=False, error="评论不存在")

        comment.is_approved = True
        comment.approved_by = current_user.id
        comment.approved_at = datetime.now(timezone.utc)
        await db.commit()

        # 发送审核通过通知
        try:
            from shared.models.article import Article
            from shared.models.user import User
            from urllib.parse import urljoin
            import os

            # 获取文章信息
            article_query = select(Article).where(Article.id == comment.article_id)
            article_result = await db.execute(article_query)
            article = article_result.scalar_one_or_none()

            if article and comment.author_email:
                base_url = os.getenv('SITE_URL', 'http://localhost:3000')
                article_url = urljoin(base_url, f"/articles/detail?id={article.id}")

                # 通知评论者审核通过
                comment_notification_service.notify_approval_result(
                    recipient_email=comment.author_email,
                    recipient_name=comment.author_name or '用户',
                    article_title=article.title,
                    article_url=article_url,
                    is_approved=True,
                    comment_content=comment.content,
                    article_id=article.id,
                    recipient_user_id=comment.user_id
                )
        except Exception as e:
            print(f"发送审核通知失败: {e}")
            # 通知失败不影响审核

        return ApiResponse(
            success=True,
            message="评论已通过审核"
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"审核评论失败: {str(e)}")


@router.post("/admin/comments/{comment_id}/reject")
async def reject_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """拒绝评论(仅管理员)"""
    try:
        from sqlalchemy import select

        # 检查权限
        if not getattr(current_user, 'is_admin', False):
            return ApiResponse(success=False, error="需要管理员权限")

        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            return ApiResponse(success=False, error="评论不存在")

        await db.delete(comment)
        await db.commit()

        return ApiResponse(
            success=True,
            message="评论已拒绝并删除"
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"拒绝评论失败: {str(e)}")


@router.get("/spam-filter/stats")
async def get_spam_filter_stats():
    """获取垃圾过滤器统计信息"""
    try:
        stats = spam_filter.get_stats()
        return ApiResponse(
            success=True,
            data=stats
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计信息失败: {str(e)}")


@router.post("/admin/spam-filter/blacklist")
async def add_ip_to_blacklist(
        request: Request,
        current_user=Depends(jwt_required)
):
    """添加IP到黑名单(仅管理员)"""
    try:
        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        body = await request.json()
        ip_address = body.get('ip_address', '').strip()

        if not ip_address:
            return ApiResponse(success=False, error="请提供IP地址")

        spam_filter.add_ip_to_blacklist(ip_address)

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} 已添加到黑名单"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"添加失败: {str(e)}")


@router.delete("/admin/spam-filter/blacklist/{ip_address}")
async def remove_ip_from_blacklist(
        ip_address: str,
        current_user=Depends(jwt_required)
):
    """从黑名单移除IP(仅管理员)"""
    try:
        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        spam_filter.remove_ip_from_blacklist(ip_address)

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} 已从黑名单移除"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"移除失败: {str(e)}")


@router.post("/admin/spam-filter/whitelist")
async def add_ip_to_whitelist(
        request: Request,
        current_user=Depends(jwt_required)
):
    """添加IP到白名单(仅管理员)"""
    try:
        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        body = await request.json()
        ip_address = body.get('ip_address', '').strip()

        if not ip_address:
            return ApiResponse(success=False, error="请提供IP地址")

        spam_filter.add_ip_to_whitelist(ip_address)

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} 已添加到白名单"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"添加失败: {str(e)}")


@router.delete("/admin/spam-filter/whitelist/{ip_address}")
async def remove_ip_from_whitelist(
        ip_address: str,
        current_user=Depends(jwt_required)
):
    """从白名单移除IP(仅管理员)"""
    try:
        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        spam_filter.remove_ip_from_whitelist(ip_address)

        return ApiResponse(
            success=True,
            message=f"IP {ip_address} 已从白名单移除"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"移除失败: {str(e)}")


@router.put("/admin/spam-filter/config")
async def update_spam_filter_config(
        request: Request,
        current_user=Depends(jwt_required)
):
    """更新垃圾过滤器配置(仅管理员)"""
    try:
        # 检查权限
        if not getattr(current_user, 'is_admin', False) and not getattr(current_user, 'is_superuser', False):
            return ApiResponse(success=False, error="需要管理员权限")

        body = await request.json()
        config = body.get('config', {})

        success = spam_filter.update_config(config)

        if success:
            return ApiResponse(
                success=True,
                message="配置更新成功",
                data=spam_filter.get_stats()
            )
        else:
            return ApiResponse(success=False, error="配置更新失败")

    except Exception as e:
        return ApiResponse(success=False, error=f"更新配置失败: {str(e)}")


@router.post("/comments/{comment_id}/like")
async def like_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    点赞/取消点赞评论
    
    Args:
        comment_id: 评论ID
    """
    try:
        result = await comment_like_service.toggle_like(
            db=db,
            user_id=current_user.id,
            comment_id=comment_id
        )

        if result['success']:
            return ApiResponse(
                success=True,
                data=result,
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"操作失败: {str(e)}")


@router.get("/comments/{comment_id}/likes")
async def get_comment_likes(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取评论的点赞数
    
    Args:
        comment_id: 评论ID
    """
    try:
        result = await comment_like_service.get_comment_likes(
            db=db,
            comment_id=comment_id
        )

        if result['success']:
            return ApiResponse(
                success=True,
                data=result
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取失败: {str(e)}")


@router.get("/comments/{comment_id}/like/status")
async def check_like_status(
        comment_id: int,
        current_user=Depends(jwt_required)
):
    """
    检查当前用户是否已点赞某条评论
    
    Args:
        comment_id: 评论ID
    """
    try:
        is_liked = await comment_like_service.check_user_like(
            user_id=current_user.id,
            comment_id=comment_id
        )

        return ApiResponse(
            success=True,
            data={
                "comment_id": comment_id,
                "is_liked": is_liked
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"检查失败: {str(e)}")


@router.get("/notifications/comments")
async def get_comment_notifications(
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    获取用户的评论相关通知
    
    Args:
        page: 页码
        per_page: 每页数量
    """
    try:
        result = await comment_notification_service.get_user_comment_notifications(
            db=db,
            user_id=current_user.id,
            page=page,
            per_page=per_page
        )

        if result['success']:
            return ApiResponse(
                success=True,
                data=result
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"获取通知失败: {str(e)}")


@router.get("/notifications/preferences")
async def get_notification_preferences(
        current_user=Depends(jwt_required)
):
    """
    获取用户的通知偏好设置
    """
    try:
        preferences = await comment_notification_service.get_user_preferences(
            user_id=current_user.id
        )

        return ApiResponse(
            success=True,
            data={
                "preferences": preferences
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取偏好失败: {str(e)}")


@router.put("/notifications/preferences")
async def update_notification_preferences(
        request: Request,
        current_user=Depends(jwt_required)
):
    """
    更新用户的通知偏好设置
    
    Body参数:
        preferences: 偏好设置字典
            - notify_on_reply: 回复时通知 (bool)
            - notify_on_new_comment: 新评论时通知 (bool)
            - email_on_reply: 回复时发送邮件 (bool)
            - email_on_new_comment: 新评论时发送邮件 (bool)
    """
    try:
        body = await request.json()
        preferences = body.get('preferences', {})

        success = await comment_notification_service.update_user_preference(
            user_id=current_user.id,
            preferences=preferences
        )

        if success:
            return ApiResponse(
                success=True,
                message="偏好设置已更新",
                data={
                    "preferences": await comment_notification_service.get_user_preferences(
                        user_id=current_user.id
                    )
                }
            )
        else:
            return ApiResponse(success=False, error="更新失败")

    except Exception as e:
        return ApiResponse(success=False, error=f"更新失败: {str(e)}")
