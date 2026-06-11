"""
评论管理API - 包含垃圾评论过滤
"""
from datetime import datetime
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.comment import Comment, CommentVote
from shared.services.comments.comment_manager import comment_like_service, comment_notification_service
from shared.services.notifications.webhook_service import webhook_service
from shared.services.plugins.event_bus import event_bus
from shared.services.security.spam_filter_manager import spam_filter
from shared.services.users.user_manager import gravatar_service
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.auth.auth_deps import jwt_optional_dependency
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["comments"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fail(str(e))
    return wrapper


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


@router.post("/")
@_catch
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
    from sqlalchemy import select
    import json

    # 1. 检查文章是否存在
    from shared.models.article import Article
    article_query = select(Article).where(Article.id == comment_data.article_id)
    article_result = await db.execute(article_query)
    article = article_result.scalar_one_or_none()

    if not article:
        return fail("文章不存在")

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

    # 5. 敏感词过滤检查
    from shared.services.security.sensitive_word_service import sensitive_word_service
    sensitive_check = await sensitive_word_service.check_content(comment_data.content)

    # 如果包含需要拦截的敏感词，直接拒绝
    if sensitive_check['has_sensitive'] and 'block' in sensitive_check['actions']:
        return fail(
            "评论包含违规内容，已拒绝",
        )

    # 如果有警告级别的敏感词，标记为待审核
    if sensitive_check['has_sensitive'] and 'warn' in sensitive_check['actions']:
        is_approved = False  # 强制待审核
    else:
        # 根据垃圾检测结果决定审核状态
        is_approved = spam_check['action'] == 'approve'

    # 6. 如果内容需要替换敏感词，进行替换
    filtered_content = comment_data.content
    if sensitive_check['has_sensitive'] and 'replace' in sensitive_check['actions']:
        filtered_content, _ = await sensitive_word_service.filter_content(comment_data.content)

    # 5. 根据检测结果决定操作
    if spam_check['action'] == 'reject':
        return fail("评论被识别为垃圾内容，已拒绝")

    # 7. 创建评论
    new_comment = Comment(
        article_id=comment_data.article_id,
        user_id=current_user.id if current_user else None,
        parent_id=comment_data.parent_id,
        content=filtered_content,  # 使用过滤后的内容
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

    # 8. 发送通知(如果评论通过审核)
    if is_approved:
        try:
            from shared.models.article import Article
            from shared.models.user import User
            from urllib.parse import urljoin
            import os

            article_query = select(Article).where(Article.id == comment_data.article_id)
            article_result = await db.execute(article_query)
            article = article_result.scalar_one_or_none()

            # 触发关注插件的评论事件
            try:
                commenter_id = current_user.id if current_user else None
                if commenter_id and article:
                    await event_bus.emit('comment.created', {
                        'user_id': str(commenter_id),
                        'article_id': article.id,
                        'article_title': article.title,
                        'content': new_comment.content,
                    })
            except Exception as plugin_err:
                print(f"Trigger plugin event failed: {plugin_err}")

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

    # 触发 Webhook 事件
    try:
        await webhook_service.trigger_event(
            'comment.created',
            {
                'comment_id': new_comment.id,
                'article_id': comment_data.article_id,
                'author_id': current_user.id if current_user else None,
                'author_name': current_user.username if current_user else comment_data.author_name or '访客',
                'content_preview': new_comment.content[:200],
                'is_approved': new_comment.is_approved,
                'created_at': new_comment.created_at.isoformat() if new_comment.created_at else None,
            },
            db=db
        )
    except Exception as webhook_err:
        print(f"Webhook trigger failed: {webhook_err}")

    return ok(
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
        msg="评论提交成功" if is_approved else "评论已提交，等待审核"
    )


@router.get("/comments/{comment_id}")
@_catch
async def get_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """获取单条评论详情"""
    from sqlalchemy import select

    query = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        return fail("评论不存在")

    return ok(
        data=comment.to_dict()
    )


@router.get("/article/{article_id}")
@_catch
async def get_article_comments(
        article_id: int,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'latest',  # latest | oldest | popular
        order: str = 'desc',  # asc | desc (仅用于兼容)
        tree: bool = False,  # 是否返回树形结构
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章的评论

    Args:
        article_id: 文章ID
        page: 页码
        per_page: 每页数量
        sort_by: 排序方式 (latest-最新, oldest-最早, popular-最热)
        order: 排序方向 (asc-升序, desc-降序) - 仅用于向后兼容
        tree: 是否返回树形结构（嵌套回复）
    """
    from sqlalchemy import select, func
    from shared.models.user import User

    # 验证排序参数
    valid_sort_fields = ['latest', 'oldest', 'popular', 'created_at', 'likes']
    if sort_by not in valid_sort_fields:
        sort_by = 'latest'

    offset = (page - 1) * per_page

    # 构建基础查询
    query = select(Comment).where(Comment.article_id == article_id)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 排序
    if sort_by in ('latest', 'created_at') or order == 'desc':
        query = query.order_by(Comment.created_at.desc())
    elif sort_by in ('oldest',):
        query = query.order_by(Comment.created_at.asc())
    elif sort_by in ('popular', 'likes'):
        query = query.order_by(Comment.likes.desc(), Comment.created_at.desc())

    # 分页
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    comments = result.scalars().all()

    # 获取所有用户信息
    user_ids = [c.user_id for c in comments if c.user_id]
    users = {}
    if user_ids:
        user_query = select(User).where(User.id.in_(user_ids))
        user_result = await db.execute(user_query)
        users = {u.id: u for u in user_result.scalars().all()}

    # 格式化评论
    comments_data = []
    for comment in comments:
        comment_dict = comment.to_dict()

        # 添加用户信息
        user = users.get(comment.user_id)
        if user:
            comment_dict['user'] = {
                'id': user.id,
                'username': user.username,
                'avatar': gravatar_service.get_avatar_url(user.email) if hasattr(gravatar_service,
                                                                                   'get_avatar_url') else None,
            }

        comments_data.append(comment_dict)

    # 如果要求树形结构
    if tree:
        tree_data = _build_comment_tree(comments_data)
        result_data = {
            'comments': tree_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
            'tree': True,
        }
    else:
        result_data = {
            'comments': comments_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
        }

    return ok(data=result_data)


@router.get("/article/{article_id}/count")
@_catch
async def get_article_comment_count(
        article_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章的评论数量

    Args:
        article_id: 文章ID
    """
    from sqlalchemy import select, func

    count_query = select(func.count()).select_from(Comment).where(
        Comment.article_id == article_id
    )
    count_result = await db.execute(count_query)
    count = count_result.scalar()

    return ok(data={
        'article_id': article_id,
        'comment_count': count,
    })


@router.get("/recent")
@_catch
async def get_recent_comments(
        limit: int = 10,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """获取最近的评论

    Args:
        limit: 返回数量
    """
    from sqlalchemy import select, desc
    from shared.models.article import Article
    from shared.models.user import User

    query = (
        select(Comment)
        .order_by(desc(Comment.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    # 获取关联的文章和用户
    article_ids = list(set([c.article_id for c in comments]))
    user_ids = list(set([c.user_id for c in comments if c.user_id]))

    articles = {}
    if article_ids:
        article_query = select(Article).where(Article.id.in_(article_ids))
        article_result = await db.execute(article_query)
        articles = {a.id: a for a in article_result.scalars().all()}

    users = {}
    if user_ids:
        user_query = select(User).where(User.id.in_(user_ids))
        user_result = await db.execute(user_query)
        users = {u.id: u for u in user_result.scalars().all()}

    comments_data = []
    for comment in comments:
        article = articles.get(comment.article_id)
        user = users.get(comment.user_id)

        comment_dict = comment.to_dict()
        comment_dict['article_title'] = article.title if article else '未知文章'
        comment_dict['user'] = {
            'id': user.id,
            'username': user.username,
        } if user else None

        comments_data.append(comment_dict)

    return ok(data={
        'comments': comments_data,
        'total': len(comments_data),
    })


@router.put("/{comment_id}")
@_catch
async def update_comment(
        comment_id: int,
        comment_data: UpdateCommentRequest,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    更新评论内容

    Args:
        comment_id: 评论ID
        comment_data: 更新数据
    """
    from sqlalchemy import select

    query = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        return fail("评论不存在")

    # 检查权限 - 只有评论作者或管理员可以编辑
    if comment.user_id != current_user.id and not getattr(current_user, 'is_staff', False):
        return fail("没有权限编辑此评论")

    comment.content = comment_data.content
    comment.updated_at = datetime.now()
    await db.commit()
    await db.refresh(comment)

    return ok(
        data=comment.to_dict(),
        msg="评论已更新"
    )


@router.delete("/{comment_id}")
@_catch
async def delete_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    删除评论(管理员或评论作者可用)
    """
    from sqlalchemy import select
    from datetime import datetime

    query = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        return fail("评论不存在")

    # 检查权限 - 只有评论作者或管理员可以删除
    if comment.user_id != current_user.id and not getattr(current_user, 'is_staff', False):
        return fail("没有权限删除此评论")

    now = datetime.now()
    comment.deleted_at = now
    comment.content = "[评论已被删除]"
    comment.is_approved = False
    comment.updated_at = now

    await db.commit()

    return ok(msg="评论已删除")


@router.get("/spam/config")
@_catch
async def get_spam_config(
        current_user=Depends(jwt_required)
):
    """获取垃圾评论检测配置"""
    if not getattr(current_user, 'is_staff', False) and not getattr(current_user, 'is_superuser', False):
        return fail("需要管理员权限")

    return ok(data={
        'config': spam_filter.get_config(),
        'stats': spam_filter.get_stats(),
    })


@router.post("/spam/config")
@_catch
async def update_spam_config(
        request: Request,
        current_user=Depends(jwt_required)
):
    """更新垃圾评论检测配置"""
    if not getattr(current_user, 'is_staff', False) and not getattr(current_user, 'is_superuser', False):
        return fail("需要管理员权限")

    body = await request.json()
    config = body.get('config', {})

    success = spam_filter.update_config(config)

    if success:
        return ok(
            msg="配置更新成功",
            data=spam_filter.get_stats()
        )
    else:
        return fail("配置更新失败")


@router.post("/{comment_id}/like")
@_catch
async def like_comment(
        comment_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    点赞/取消点赞评论（增强版）

    支持：
    - 首次点赞
    - 取消点赞
    - 从反对改为点赞

    Args:
        comment_id: 评论ID
    """
    from sqlalchemy import select
    from datetime import datetime

    # 检查评论是否存在
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if not comment:
        return fail("评论不存在")

    # 检查是否已经投票
    stmt = select(CommentVote).where(
        CommentVote.comment_id == comment_id,
        CommentVote.user == current_user.id
    )
    result = await db.execute(stmt)
    existing_vote = result.scalar_one_or_none()

    if existing_vote:
        if existing_vote.vote_type == 1:
            # 已经点赞，取消点赞
            await db.delete(existing_vote)
            comment.likes = max(0, comment.likes - 1)
            action = 'unliked'
            message = '已取消点赞'
        else:
            # 之前是反对，改为点赞
            existing_vote.vote_type = 1
            comment.likes += 1
            action = 'liked'
            message = '点赞成功'
    else:
        # 新建点赞
        vote = CommentVote(
            comment_id=comment_id,
            user=current_user.id,
            vote_type=1,
            ip_address=request.client.host if request.client else None,
            created_at=datetime.now()
        )
        db.add(vote)
        comment.likes += 1
        action = 'liked'
        message = '点赞成功'

    await db.commit()
    await db.refresh(comment)

    return ok(
        data={
            'action': action,
            'likes': comment.likes,
            'vote_type': 1 if action == 'liked' else None
        },
        msg=message
    )


@router.post("/{comment_id}/dislike")
@_catch
async def dislike_comment(
        comment_id: int,
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    反对/取消反对评论

    支持：
    - 首次反对
    - 取消反对
    - 从点赞改为反对

    Args:
        comment_id: 评论ID
    """
    from shared.models.comment_vote import CommentVote
    from sqlalchemy import select
    from datetime import datetime

    # 检查评论是否存在
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if not comment:
        return fail("评论不存在")

    # 检查是否已经投票
    stmt = select(CommentVote).where(
        CommentVote.comment_id == comment_id,
        CommentVote.user == current_user.id
    )
    result = await db.execute(stmt)
    existing_vote = result.scalar_one_or_none()

    if existing_vote:
        if existing_vote.vote_type == -1:
            # 已经反对，取消反对
            await db.delete(existing_vote)
            action = 'undisliked'
            message = '已取消反对'
        else:
            # 之前是点赞，改为反对
            existing_vote.vote_type = -1
            comment.likes = max(0, comment.likes - 1)
            action = 'disliked'
            message = '已反对'
    else:
        # 新建反对
        vote = CommentVote(
            comment_id=comment_id,
            user=current_user.id,
            vote_type=-1,
            ip_address=request.client.host if request.client else None,
            created_at=datetime.now()
        )
        db.add(vote)
        comment.likes = max(0, comment.likes - 1)
        action = 'disliked'
        message = '已反对'

    await db.commit()
    await db.refresh(comment)

    return ok(
        data={
            'action': action,
            'likes': comment.likes,
            'vote_type': -1 if action == 'disliked' else None
        },
        msg=message
    )


@router.get("/{comment_id}/likes")
@_catch
async def get_comment_likes(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取评论的点赞数

    Args:
        comment_id: 评论ID
    """
    result = await comment_like_service.get_comment_likes(
        db=db,
        comment_id=comment_id
    )

    if result['success']:
        return ok(data=result)
    else:
        return fail(result['error'])


@router.get("/{comment_id}/vote")
@_catch
async def get_user_vote(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    获取用户对评论的投票状态

    Args:
        comment_id: 评论ID

    Returns:
        vote_type: 1 (赞) | -1 (踩) | null
    """
    from shared.models.comment_vote import CommentVote
    from sqlalchemy import select

    stmt = select(CommentVote).where(
        CommentVote.comment_id == comment_id,
        CommentVote.user == current_user.id
    )
    result = await db.execute(stmt)
    vote = result.scalar_one_or_none()

    vote_type = vote.vote_type if vote else None

    return ok(data={
        "comment_id": comment_id,
        "vote_type": vote_type
    })


@router.post("/{comment_id}/notify-reply")
@_catch
async def notify_comment_reply(
        comment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    通知评论被回复（通常在创建回复评论后调用）

    Args:
        comment_id: 新评论ID

    Returns:
        通知结果
    """
    from shared.models.notification import Notification
    from sqlalchemy import select

    # 获取新评论
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(stmt)
    new_comment = result.scalar_one_or_none()

    if not new_comment or not new_comment.parent_id:
        return fail("不是回复评论")

    # 获取父评论
    stmt = select(Comment).where(Comment.id == new_comment.parent_id)
    result = await db.execute(stmt)
    parent_comment = result.scalar_one_or_none()

    if not parent_comment or not parent_comment.user_id:
        return fail("父评论没有用户")

    # 如果是自己回复自己，不发送通知
    if parent_comment.user_id == new_comment.user_id:
        return fail("自己回复自己")

    # 创建通知
    notification = Notification(
        user_id=parent_comment.user_id,
        type='comment_reply',
        title='有人回复了你的评论',
        content=f'{new_comment.author_name or "匿名用户"} 回复了你的评论',
        related_id=new_comment.id,
        related_type='comment',
        is_read=False
    )

    db.add(notification)
    await db.commit()

    return ok(
        data={
            'notification_id': notification.id
        },
        msg="通知已发送"
    )


# ==================== 辅助函数 ====================

def _build_comment_tree(comments: list) -> list:
    """
    构建评论树形结构

    Args:
        comments: 评论列表（字典格式）

    Returns:
        树形结构的评论列表
    """
    # 转换为字典并添加 children 字段
    comment_map = {}
    for comment in comments:
        comment_dict = comment.copy() if isinstance(comment, dict) else comment.to_dict()
        comment_dict['children'] = []
        comment_dict['depth'] = 0
        comment_map[comment_dict['id']] = comment_dict

    # 构建树
    root_comments = []
    for comment_dict in comment_map.values():
        parent_id = comment_dict.get('parent_id')

        if parent_id is None or parent_id not in comment_map:
            # 根评论
            root_comments.append(comment_dict)
        else:
            # 子评论，添加到父评论的 children
            parent = comment_map[parent_id]
            comment_dict['depth'] = parent['depth'] + 1
            parent['children'].append(comment_dict)

    return root_comments


@router.get("/notifications/comments")
@_catch
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
    result = await comment_notification_service.get_user_comment_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page
    )

    if result['success']:
        return ok(data=result)
    else:
        return fail(result['error'])


@router.get("/notifications/preferences")
@_catch
async def get_notification_preferences(
        current_user=Depends(jwt_required)
):
    """
    获取用户的通知偏好设置
    """
    preferences = await comment_notification_service.get_user_preferences(
        user_id=current_user.id
    )

    return ok(data={
        "preferences": preferences
    })


@router.put("/notifications/preferences")
@_catch
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
    body = await request.json()
    preferences = body.get('preferences', {})

    success = await comment_notification_service.update_user_preference(
        user_id=current_user.id,
        preferences=preferences
    )

    if success:
        return ok(
            msg="偏好设置已更新",
            data={
                "preferences": await comment_notification_service.get_user_preferences(
                    user_id=current_user.id
                )
            }
        )
    else:
        return fail("更新失败")
