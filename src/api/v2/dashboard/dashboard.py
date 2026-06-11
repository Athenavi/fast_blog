"""
仪表板相关 API
"""

import re
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import desc
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import VIPPlan, VIPFeature
from shared.models.analytics import UserActivity
from shared.models.article import Article
from shared.models.category import Category
from shared.models.media import Media, FileHash
from shared.models.notification import Notification
from shared.models.user import User
# 导入 SQLAlchemy 模型和服务
from shared.models.user import User as UserModel
from shared.models.vip import VIPSubscription
# 注意：避免在此处直接导入 article_service，防止循环依赖
# article_service 的导入已移至使用位置
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import admin_required as admin_required_api, jwt_required_dependency as jwt_required, \
    get_current_active_user
from src.extensions import get_async_db_session as get_async_db

router = APIRouter()


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


@router.get("/activities")
@_catch
async def get_activities(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=50),
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """获取最近用户活动列表"""
    offset = (page - 1) * per_page
    query = select(UserActivity).order_by(desc(UserActivity.created_at)).offset(offset).limit(per_page)
    result = await db.execute(query)
    activities = result.scalars().all()

    data = [
        {
            "message": f"{a.activity_type or ''} - {a.details or ''}",
            "action": a.activity_type,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]
    return ok(data=data)


@router.get("/stats")
@_catch
async def get_dashboard_stats(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取仪表板统计数据
    """
    from datetime import datetime, timedelta

    # 计算总用户数
    total_users_query = select(func.count()).select_from(User)
    total_users_result = await db.execute(total_users_query)
    total_users = total_users_result.scalar()

    # 计算总文章数
    total_articles_query = select(func.count()).select_from(Article)
    total_articles_result = await db.execute(total_articles_query)
    total_articles = total_articles_result.scalar()

    # 计算总点赞数 (使用Article模型中的likes字段)
    total_likes_query = select(func.sum(Article.likes))
    total_likes_result = await db.execute(total_likes_query)
    total_likes = total_likes_result.scalar() or 0

    # 计算总浏览量
    total_views_query = select(func.sum(Article.views))
    total_views_result = await db.execute(total_views_query)
    total_views = total_views_result.scalar() or 0

    # 获取最近一周的用户注册数
    week_ago = datetime.now() - timedelta(days=7)
    new_users_query = select(func.count()).select_from(User).where(User.date_joined >= week_ago)
    new_users_result = await db.execute(new_users_query)
    new_users = new_users_result.scalar()

    stats_data = {
        "visitors": total_views,  # 使用真实浏览量
        "articles": total_articles,
        "comments": 0,  # 暂时设为0，因为评论模型未定义
        "likes": total_likes,
        "users": total_users,
        "new_users": new_users
    }

    return ok(data=stats_data)


@router.get("/recent-articles")
@_catch
async def __get_recent_articles(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取最近的文章
    """
    from sqlalchemy.orm import selectinload

    # 查询最近的文章（按创建时间排序），使用预加载来避免N+1问题
    recent_articles_query = select(Article).order_by(
        desc(Article.created_at)).limit(4)
    recent_articles_result = await db.execute(recent_articles_query)
    recent_articles = recent_articles_result.scalars().all()

    articles_data = []
    for article in recent_articles:
        # 获取作者信息（由于 author 关系已注释，使用 user_id）
        author_username = "Unknown"  # 暂时显示 Unknown
        articles_data.append({
            "id": article.id,
            "title": article.title,
            "author": author_username,
            "views": getattr(article, 'views', 0),
            "comments": 0,  # 暂时设为 0，因为评论模型未定义
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "status": "published" if getattr(article, 'status', 0) == 1 else "draft"  # status 为 1 表示 published
        })

    return ok(data=articles_data)


@router.get("/traffic")
@_catch
async def get_traffic_data(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取流量数据
    """
    from datetime import datetime, timedelta

    # 计算过去7天每天的文章浏览量
    traffic_data = []
    for i in range(7):
        date_start = datetime.now() - timedelta(days=i)
        date_end = date_start + timedelta(days=1)
        date_start = date_start.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_end.replace(hour=0, minute=0, second=0, microsecond=0)

        # 计算当天的文章浏览量总和
        daily_views_query = select(func.sum(Article.views)).where(
            Article.created_at >= date_start,
            Article.created_at < date_end
        )
        daily_views_result = await db.execute(daily_views_query)
        daily_views = daily_views_result.scalar() or 0

        traffic_data.append({
            "date": date_start.strftime("%m-%d"),
            "visitors": daily_views
        })

    # 按日期升序排列
    traffic_data.reverse()

    return ok(data=traffic_data)


@router.get("/blog-management/articles")
@_catch
async def get_blog_management_articles(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        category_id: Optional[int] = Query(None),
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取博客管理文章列表
    """
    # 使用SQLAlchemy异步查询语法
    # 构建基础查询（category 是外键字段，不是 relationship，不能直接使用 selectinload）
    query = select(Article)

    # 根据状态过滤
    if status:
        # 转换为小写以匹配映射
        status_lower = status.lower()
        status_map = {'published': 1, 'draft': 0, 'deleted': -1}
        if status_lower in status_map:
            query = query.where(Article.status == status_map[status_lower])

    # 根据搜索词过滤
    if search:
        query = query.where(Article.title.contains(search))

    # 根据分类ID过滤
    if category_id:
        query = query.where(Article.category == category_id)

    # 计算总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * per_page
    articles_query = query.offset(offset).limit(per_page)
    articles_result = await db.execute(articles_query)
    articles = articles_result.scalars().all()

    articles_data = []
    for article in articles:
        # 使用模型的 to_dict() 方法获取基础数据
        article_dict = article.to_dict()

        # 确定文章状态（转换为字符串）
        article_status = 'draft'
        if article.status == 1:
            article_status = 'published'
        elif article.status == 0:
            article_status = 'draft'
        elif article.status == -1:
            article_status = 'deleted'

        # 获取作者信息（由于 author 关系已注释，需要手动查询）
        from shared.models.user import User
        author_query = select(User).where(User.id == article.user)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()
        author_info = {
            "id": author.id if author else article.user,
            "username": getattr(author, 'username', 'Unknown') if author else 'Unknown',
            "email": getattr(author, 'email', '') if author else ''
        }

        # 获取分类信息
        category_info = None
        if article.category:
            category_query = select(Category).where(Category.id == article.category)
            category_result = await db.execute(category_query)
            category = category_result.scalar_one_or_none()
            if category:
                category_info = {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description
                }

        # 处理标签（将 tags_list 字符串转换为数组，支持逗号和分号分隔符）
        tags_list = []
        if article_dict.get('tags_list'):
            if isinstance(article_dict['tags_list'], str):
                tags_list = [tag.strip() for tag in re.split(r'[,;]', article_dict['tags_list']) if tag.strip()]
            else:
                tags_list = article_dict['tags_list']

        # 构建响应数据，在 to_dict() 基础上添加关联数据
        articles_data.append({
            **article_dict,  # 展开模型的基础字段
            "summary": article_dict.get('excerpt', ''),  # summary 是 excerpt 的别名
            "tags": tags_list,  # 转换后的标签数组
            "views_count": article_dict.get('views', 0),  # 前端期望的字段名
            "status": article_status,  # 覆盖为字符串状态
            "author": author_info,  # 添加作者信息
            "category": category_info,  # 添加分类信息
        })

    return ok(
        data=articles_data,
    )


@router.get("/my/articles")
@_catch
async def get_my_articles(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        hidden: Optional[bool] = Query(None),
        category_id: Optional[int] = Query(None, description="按分类 ID 筛选"),
        tag: Optional[str] = Query(None, description="按标签筛选"),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我的文章列表
    """
    from sqlalchemy import or_

    # 构建基础查询，预加载关联的作者信息
    query = select(Article).join(User, Article.user == User.id).where(
        Article.user == current_user.id)

    # 根据状态过滤
    if status:
        # 转换为小写以匹配映射
        status_lower = status.lower()
        status_map = {'published': 1, 'draft': 0, 'deleted': -1}
        if status_lower in status_map:
            query = query.where(Article.status == status_map[status_lower])

    # 根据隐藏状态过滤
    if hidden is not None:
        query = query.where(Article.hidden == hidden)

    # 根据分类过滤
    if category_id is not None:
        query = query.where(Article.category == category_id)

    # 根据标签过滤（在 tags_list 字段中搜索）
    if tag:
        query = query.where(Article.tags_list.contains(tag))

    # 根据搜索词过滤
    if search:
        # 支持按标题搜索，也可以按内容搜索（但内容表不同，此处仅搜索标题）
        query = query.where(Article.title.contains(search))

    # 按创建时间降序排列
    query = query.order_by(desc(Article.created_at))

    # 计算总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # 分页
    offset_val = (page - 1) * per_page
    paginated_query = query.offset(offset_val).limit(per_page)
    paginated_result = await db.execute(paginated_query)
    articles = paginated_result.scalars().all()

    # 构建响应数据
    articles_data = []
    for article in articles:
        article_obj = article.to_dict()

        # 处理状态
        article_status = 'draft'
        if article.status == 1:
            article_status = 'published'
        elif article.status == -1:
            article_status = 'deleted'

        # 处理标签
        tags_list = []
        if article_obj.get('tags_list'):
            if isinstance(article_obj['tags_list'], str):
                tags_list = [tag.strip() for tag in re.split(r'[,;]', article_obj['tags_list']) if tag.strip()]
            else:
                tags_list = article_obj['tags_list']

        # 获取分类名
        category_name = None
        if article.category:
            cat_query = select(Category).where(Category.id == article.category)
            cat_result = await db.execute(cat_query)
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        articles_data.append({
            **article_obj,
            "status": article_status,
            "tags": tags_list,
            "category_name": category_name,
            "views_count": article_obj.get('views', 0),
            "summary": article_obj.get('excerpt', ''),
        })

    return ok(
        data={
            "articles": articles_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }
    )


@router.get("/blog-management/vip")
@_catch
async def get_vip_management_data(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取 VIP 管理数据
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    month_ago = now - timedelta(days=30)

    # 统计
    total_result = await db.execute(select(func.count(VIPSubscription.id)))
    total_count = total_result.scalar() or 0

    monthly_result = await db.execute(
        select(func.count(VIPSubscription.id)).where(VIPSubscription.created_at >= month_ago)
    )
    monthly_new = monthly_result.scalar() or 0

    # 查询所有订阅
    subscriptions_query = (
        select(VIPSubscription)
        .join(VIPPlan, VIPSubscription.plan == VIPPlan.id, isouter=True)
    )
    subscriptions_result = await db.execute(subscriptions_query)
    subscriptions = subscriptions_result.scalars().all()

    monthly_revenue = 0.0
    members_data = []
    for sub in subscriptions:
        amt = float(sub.payment_amount) if sub.payment_amount else 0.0
        if sub.created_at and sub.created_at >= month_ago:
            monthly_revenue += amt
        is_active = bool(sub.status == 1 and sub.expires_at and sub.expires_at > now)
        username = sub.user.username if sub.user else "Unknown"
        plan_name = sub.plan.name if sub.plan else "Unknown"
        level = sub.plan.level if sub.plan else 0
        members_data.append({
            "id": sub.id,
            "user_id": sub.user_id,
            "username": username,
            "plan_name": plan_name,
            "level": level,
            "starts_at": sub.starts_at.isoformat() if sub.starts_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "is_active": is_active,
            "amount": amt,
            "transaction_id": sub.transaction_id,
            "status": "active" if sub.status == 1 else "inactive",
        })

    active_members = sum(1 for m in members_data if m['is_active'])
    renewal_rate = round(active_members / total_count * 100, 1) if total_count > 0 else 0

    # 所有计划
    plans_result = await db.execute(select(VIPPlan).order_by(VIPPlan.level))
    plans = plans_result.scalars().all()

    # 所有功能
    features_result = await db.execute(select(VIPFeature).order_by(VIPFeature.required_level))
    features = features_result.scalars().all()

    return ok(data={
        "stats": {
            "total_vip_count": total_count,
            "active_count": active_members,
            "monthly_new": monthly_new,
            "monthly_revenue": round(monthly_revenue, 2),
            "renewal_rate": renewal_rate,
        },
        "members": members_data,
        "plans": [p.to_dict() for p in plans],
        "features": [f.to_dict() for f in features],
    })


@router.get("/blog-management/articles/stats")
@_catch
async def get_blog_management_articles_stats(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取博客管理文章统计信息
    """
    # 计算文章总数
    total_articles_query = select(func.count(Article.id))
    total_articles_result = await db.execute(total_articles_query)
    total_articles = total_articles_result.scalar()

    # 计算已发布文章数
    published_articles_query = select(func.count(Article.id)).where(Article.status == 1)
    published_articles_result = await db.execute(published_articles_query)
    published_articles = published_articles_result.scalar()

    # 计算草稿文章数
    draft_articles_query = select(func.count(Article.id)).where(Article.status == 0)
    draft_articles_result = await db.execute(draft_articles_query)
    draft_articles = draft_articles_result.scalar()

    # 计算总浏览量
    total_views_query = select(func.sum(Article.views))
    total_views_result = await db.execute(total_views_query)
    total_views = total_views_result.scalar() or 0

    stats_data = {
        "total_articles": total_articles,
        "published_articles": published_articles,
        "draft_articles": draft_articles,
        "total_views": total_views
    }

    return ok(data=stats_data)


@router.delete("/blog-management/articles/{article_id}")
@_catch
async def delete_blog_management_article(
        request: Request,
        article_id: int,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除博客管理文章
    """
    from sqlalchemy import select, delete
    from shared.models.article_content import ArticleContent
    from shared.models.article_revision import ArticleRevision

    article_query = select(Article).where(Article.id == article_id)
    article_result = await db.execute(article_query)
    article = article_result.scalar_one_or_none()
    if not article:
        return fail("Article not found")

    # 检查权限 - 只有超级用户或文章作者可以删除
    if not current_user.is_superuser and article.user != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 级联删除评论投票（先于评论删除，避免孤立记录）
    from shared.models.comment import Comment
    from shared.models.comment_vote import CommentVote
    from shared.models.comment_subscription import CommentSubscription

    comment_ids_result = await db.execute(
        select(Comment.id).where(Comment.article_id == article_id)
    )
    comment_ids = [row[0] for row in comment_ids_result.all()]
    if comment_ids:
        await db.execute(
            delete(CommentVote).where(CommentVote.comment_id.in_(comment_ids))
        )

    # 级联删除评论订阅
    await db.execute(
        delete(CommentSubscription).where(CommentSubscription.article_id == article_id)
    )

    # 级联删除评论
    await db.execute(
        delete(Comment).where(Comment.article_id == article_id)
    )

    # 级联删除修订历史
    revisions_query = select(ArticleRevision).where(ArticleRevision.article_id == article_id)
    revisions_result = await db.execute(revisions_query)
    for revision in revisions_result.scalars().all():
        await db.delete(revision)

    # 级联删除内容
    content_query = select(ArticleContent).where(ArticleContent.article == article_id)
    content_result = await db.execute(content_query)
    for content in content_result.scalars().all():
        await db.delete(content)

    await db.delete(article)
    await db.commit()

    return ok(data={"message": "Article deleted successfully"})


# ====== VIP 计划管理 (Admin) ======

@router.post("/vip/plans")
@_catch
async def admin_create_vip_plan(
    request: Request,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """创建 VIP 套餐"""
    form = await request.form()
    plan = VIPPlan(
        name=form.get('name'),
        description=form.get('description', ''),
        price=float(form.get('price', 0)),
        original_price=float(form.get('original_price', 0)) if form.get('original_price') else None,
        duration_days=int(form.get('duration_days', 30)),
        level=int(form.get('level', 1)),
        features=form.get('features', '[]'),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return ok(data=plan.to_dict())


@router.put("/vip/plans/{plan_id}")
@_catch
async def admin_update_vip_plan(
    request: Request,
    plan_id: int,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """更新 VIP 套餐"""
    result = await db.execute(select(VIPPlan).where(VIPPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return fail("套餐不存在")

    form = await request.form()
    plan.name = form.get('name', plan.name)
    plan.description = form.get('description', plan.description)
    plan.price = float(form.get('price', plan.price))
    plan.original_price = float(form.get('original_price', plan.original_price)) if form.get('original_price') else plan.original_price
    plan.duration_days = int(form.get('duration_days', plan.duration_days))
    plan.level = int(form.get('level', plan.level))
    plan.features = form.get('features', plan.features)
    is_active = form.get('is_active')
    if is_active is not None:
        plan.is_active = is_active in ('1', 'true', 'True', True)
    await db.commit()
    await db.refresh(plan)
    return ok(data=plan.to_dict())


@router.delete("/vip/plans/{plan_id}")
@_catch
async def admin_delete_vip_plan(
    plan_id: int,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """删除 VIP 套餐"""
    result = await db.execute(select(VIPPlan).where(VIPPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return fail("套餐不存在")
    await db.delete(plan)
    await db.commit()
    return ok(data={"message": "已删除"})


# ====== VIP 功能管理 (Admin) ======

@router.post("/vip/features")
@_catch
async def admin_create_vip_feature(
    request: Request,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """创建 VIP 功能"""
    form = await request.form()
    feature = VIPFeature(
        code=form.get('code'),
        name=form.get('name'),
        description=form.get('description', ''),
        required_level=int(form.get('required_level', 1)),
    )
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return ok(data=feature.to_dict())


@router.put("/vip/features/{feature_id}")
@_catch
async def admin_update_vip_feature(
    request: Request,
    feature_id: int,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """更新 VIP 功能"""
    result = await db.execute(select(VIPFeature).where(VIPFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        return fail("功能不存在")

    form = await request.form()
    feature.code = form.get('code', feature.code)
    feature.name = form.get('name', feature.name)
    feature.description = form.get('description', feature.description)
    feature.required_level = int(form.get('required_level', feature.required_level))
    is_active = form.get('is_active')
    if is_active is not None:
        feature.is_active = is_active in ('1', 'true', 'True', True)
    await db.commit()
    await db.refresh(feature)
    return ok(data=feature.to_dict())


@router.delete("/vip/features/{feature_id}")
@_catch
async def admin_delete_vip_feature(
    feature_id: int,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """删除 VIP 功能"""
    result = await db.execute(select(VIPFeature).where(VIPFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        return fail("功能不存在")
    await db.delete(feature)
    await db.commit()
    return ok(data={"message": "已删除"})


@router.get("/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(admin_required_api)):
    """
    管理员面板入口

    Returns:
        管理员面板信息
    """
    return {
        'success': True,
        'message': '管理员面板',
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'is_staff': getattr(current_user, 'is_staff', False),
            'is_superuser': getattr(current_user, 'is_superuser', False)
        }
    }
