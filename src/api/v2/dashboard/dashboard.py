"""
仪表板相�?API
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import desc
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import VIPPlan, VIPFeature
from shared.models.analytics import UserActivity
from shared.models.article import Article
from shared.models.category import Category
from shared.models.user import User
# 导入 SQLAlchemy 模型和服�?from shared.models.vip import VIPSubscription
# 注意：避免在此处直接导入 article_service，防止循环依�?# article_service 的导入已移至使用位置
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import admin_required as admin_required_api, jwt_required_dependency as jwt_required
from src.utils.database.unified_manager import get_db_session as get_async_db

router = APIRouter()


async def get_activities(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(8, ge=1, le=50),
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """获取最近用户活动列�?""
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
    获取仪表板统计数�?    """
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

    # 获取最近一周的用户注册�?    week_ago = datetime.now() - timedelta(days=7)
    new_users_query = select(func.count()).select_from(User).where(User.date_joined >= week_ago)
    new_users_result = await db.execute(new_users_query)
    new_users = new_users_result.scalar()

    stats_data = {
        "visitors": total_views,  # 使用真实浏览�?        "articles": total_articles,
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

    # 查询最近的文章（按创建时间排序），使用预加载来避免N+1问题
    recent_articles_query = select(Article).order_by(
        desc(Article.created_at)).limit(4)
    recent_articles_result = await db.execute(recent_articles_query)
    recent_articles = recent_articles_result.scalars().all()

    articles_data = []
    for article in recent_articles:
        # 获取作者信息（由于 author 关系已注释，使用 user_id�?        author_username = "Unknown"  # 暂时显示 Unknown
        articles_data.append({
            "id": article.id,
            "title": article.title,
            "author": author_username,
            "views": getattr(article, 'views', 0),
            "comments": 0,  # 暂时设为 0，因为评论模型未定义
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "status": "published" if getattr(article, 'status', 0) == 1 else "draft"  # status �?1 表示 published
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

    # 计算过去7天的时间范围（包含今天）
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=6)

    # 一次性查询过�?天每天的文章浏览�?    daily_views_query = select(
        func.date(Article.created_at),
        func.coalesce(func.sum(Article.views), 0)
    ).where(
        Article.created_at >= start_date,
        Article.created_at < end_date + timedelta(days=1)
    ).group_by(
        func.date(Article.created_at)
    )
    daily_views_result = await db.execute(daily_views_query)
    daily_views_dict = dict(daily_views_result.all())

    # 按日期填�?天的数据
    traffic_data = []
    for i in range(7):
        date_start = end_date - timedelta(days=6-i)
        date_key = date_start.strftime("%Y-%m-%d")
        daily_views = daily_views_dict.get(date_key, 0) or 0

        traffic_data.append({
            "date": date_start.strftime("%m-%d"),
            "visitors": daily_views
        })

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
    # 构建基础查询（category 是外键字段，不是 relationship，不能直接使�?selectinload�?    query = select(Article)

    # 根据状态过�?    if status:
        # 转换为小写以匹配映射
        status_lower = status.lower()
        status_map = {'published': 1, 'draft': 0, 'deleted': -1}
        if status_lower in status_map:
            if status_lower == 'deleted':
                # deleted �?status=-1 �?deleted_at 标记（删除时两者同时写入）�?                # 过滤与展示逻辑保持一致，兼容历史仅设 deleted_at 的数�?                query = query.where(or_(Article.status == -1, Article.deleted_at.isnot(None)))
            else:
                query = query.where(Article.status == status_map[status_lower])

    # 根据搜索词过�?    if search:
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
    # Batch-load users & categories to eliminate N+1
    user_ids = {a.user for a in articles if a.user}
    cat_ids = {a.category for a in articles if a.category}
    from shared.models.user import User
    from shared.models.category import Category
    if user_ids:
        users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()}
    else:
        users = {}
    if cat_ids:
        categories = {c.id: c for c in (await db.execute(select(Category).where(Category.id.in_(cat_ids)))).scalars().all()}
    else:
        categories = {}

    for article in articles:
        article_dict = article.to_dict()

        # 确定文章状态（转换为字符串�?        article_status = 'draft'
        if article.status == 1:
            article_status = 'published'
        elif article.status == 0:
            article_status = 'draft'
        elif article.status == -1 or article.deleted_at is not None:
            article_status = 'deleted'

        # 作者信息（�?batch 查询�?dict 中获取）
        author = users.get(article.user)
        author_info = {
            "id": author.id if author else article.user,
            "username": getattr(author, 'username', 'Unknown') if author else 'Unknown',
            "email": getattr(author, 'email', '') if author else ''
        }

        # 分类信息（从 batch 查询�?dict 中获取）
        category_info = None
        if article.category:
            category = categories.get(article.category)
            if category:
                category_info = {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description
                }

        # 处理标签（tags_list 已经�?JSON 数组�?        tags_list = article_dict.get('tags_list') or []

        # 构建响应数据，在 to_dict() 基础上添加关联数�?        articles_data.append({
            **article_dict,  # 展开模型的基础字段
            "summary": article_dict.get('excerpt', ''),  # summary �?excerpt 的别�?            "tags": tags_list,  # 转换后的标签数组
            "views_count": article_dict.get('views', 0),  # 前端期望的字段名
            "status": article_status,  # 覆盖为字符串状�?            "author": author_info,  # 添加作者信�?            "category": category_info,  # 添加分类信息
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
        category_id: Optional[int] = Query(None, description="按分�?ID 筛�?),
        tag: Optional[str] = Query(None, description="按标签筛�?),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我的文章列表
    """
    # 构建基础查询，预加载关联的作者信�?    query = select(Article).join(User, Article.user == User.id).where(
        Article.user == current_user.id)

    # 根据状态过�?    if status:
        # 转换为小写以匹配映射
        status_lower = status.lower()
        status_map = {'published': 1, 'draft': 0, 'deleted': -1}
        if status_lower in status_map:
            if status_lower == 'deleted':
                # deleted �?status=-1 �?deleted_at 标记（删除时两者同时写入）�?                # 过滤与展示逻辑保持一致，兼容历史仅设 deleted_at 的数�?                query = query.where(or_(Article.status == -1, Article.deleted_at.isnot(None)))
            else:
                query = query.where(Article.status == status_map[status_lower])

    # 根据隐藏状态过�?    if hidden is not None:
        query = query.where(Article.hidden == hidden)

    # 根据分类过滤
    if category_id is not None:
        query = query.where(Article.category == category_id)

    # 根据标签过滤（在 tags_list 字段中搜索）
    if tag:
        query = query.where(Article.tags_list.any(tag))

    # 根据搜索词过�?    if search:
        # 支持按标题搜索，也可以按内容搜索（但内容表不同，此处仅搜索标题）
        query = query.where(Article.title.contains(search))

    # 按创建时间降序排�?    query = query.order_by(desc(Article.created_at))

    # 计算总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # 分页
    offset_val = (page - 1) * per_page
    paginated_query = query.offset(offset_val).limit(per_page)
    paginated_result = await db.execute(paginated_query)
    articles = paginated_result.scalars().all()

    # 批量加载分类，避免循环内逐条查询（N+1�?    cat_ids = {a.category for a in articles if a.category}
    if cat_ids:
        cats = {c.id: c for c in (await db.execute(select(Category).where(Category.id.in_(cat_ids)))).scalars().all()}
    else:
        cats = {}

    # 构建响应数据
    articles_data = []
    for article in articles:
        article_obj = article.to_dict()

        # 处理状�?        article_status = 'draft'
        if article.status == 1:
            article_status = 'published'
        elif article.status == -1 or article.deleted_at is not None:
            article_status = 'deleted'

        # 处理标签（tags_list 已经�?JSON 数组�?        tags_list = article_obj.get('tags_list') or []

        # 获取分类名（从批量查询的 dict 中获取）
        category_name = None
        if article.category:
            category = cats.get(article.category)
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
    current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取 VIP 管理数据（仅管理员）
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

    # 查询订阅（含用户和套餐信息），限制返回条数避免全量加�?    subscriptions_query = (
        select(VIPSubscription, User, VIPPlan)
        .join(User, VIPSubscription.user == User.id, isouter=True)
        .join(VIPPlan, VIPSubscription.plan == VIPPlan.id, isouter=True)
        .order_by(desc(VIPSubscription.created_at))
        .limit(200)
    )
    subscriptions_result = await db.execute(subscriptions_query)
    rows = subscriptions_result.all()

    monthly_revenue = 0.0
    members_data = []
    for sub, user_obj, plan_obj in rows:
        amt = float(sub.payment_amount) if sub.payment_amount else 0.0
        if sub.created_at and sub.created_at >= month_ago:
            monthly_revenue += amt
        is_active = bool(sub.status == 1 and sub.expires_at and sub.expires_at > now)
        username = user_obj.username if user_obj else "Unknown"
        plan_name = plan_obj.name if plan_obj else "Unknown"
        level = plan_obj.level if plan_obj else 0
        members_data.append({
            "id": sub.id,
            "user_id": sub.user,  # FK 列名�?user
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

    # 所有计�?    plans_result = await db.execute(select(VIPPlan).order_by(VIPPlan.level))
    plans = plans_result.scalars().all()

    # 所有功�?    features_result = await db.execute(select(VIPFeature).order_by(VIPFeature.required_level))
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

    # 计算草稿文章�?    draft_articles_query = select(func.count(Article.id)).where(Article.status == 0)
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

    # 检查权�?- 只有超级用户或文章作者可以删�?    if not current_user.is_superuser and article.user != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 级联删除评论投票（先于评论删除，避免孤立记录�?    from shared.models.comment import Comment
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
    from datetime import datetime
    body = await request.json()
    plan = VIPPlan(
        name=body.get('name'),
        description=body.get('description', ''),
        price=float(body.get('price', 0)),
        original_price=float(body.get('original_price', 0)) if body.get('original_price') else None,
        duration_days=int(body.get('duration_days', 30)),
        level=int(body.get('level', 1)),
        features=body.get('features', '[]'),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(plan)
    await db.flush()
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
    from datetime import datetime
    from sqlalchemy import update
    body = await request.json()

    vals = {}
    if body.get('name') is not None:
        vals['name'] = body['name']
    if body.get('description') is not None:
        vals['description'] = body['description']
    if body.get('price') is not None:
        vals['price'] = float(body['price'])
    if body.get('original_price') is not None and body['original_price']:
        vals['original_price'] = float(body['original_price'])
    if body.get('duration_days') is not None:
        vals['duration_days'] = int(body['duration_days'])
    if body.get('level') is not None:
        vals['level'] = int(body['level'])
    if body.get('features') is not None:
        vals['features'] = body['features']
    if body.get('is_active') is not None:
        val = body['is_active']
        vals['is_active'] = bool(val) if isinstance(val, (bool, int)) else str(val) in ('1', 'true', 'True')

    if not vals:
        return fail("没有要更新的字段")

    vals['updated_at'] = datetime.now()

    await db.execute(
        update(VIPPlan).where(VIPPlan.id == plan_id).values(**vals)
    )
    await db.flush()
    return ok(data={"message": "更新成功"})


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
        return fail("套餐不存�?)
    await db.delete(plan)
    await db.flush()
    return ok(data={"message": "已删�?})


# ====== VIP 功能管理 (Admin) ======

@router.post("/vip/features")
@_catch
async def admin_create_vip_feature(
    request: Request,
    current_user: User = Depends(admin_required_api),
    db: AsyncSession = Depends(get_async_db)
):
    """创建 VIP 功能"""
    from datetime import datetime
    body = await request.json()
    feature = VIPFeature(
        code=body.get('code'),
        name=body.get('name'),
        description=body.get('description', ''),
        required_level=int(body.get('required_level', 1)),
        created_at=datetime.now(),
    )
    db.add(feature)
    await db.flush()
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
    from sqlalchemy import update
    body = await request.json()

    vals = {}
    if body.get('code') is not None:
        vals['code'] = body['code']
    if body.get('name') is not None:
        vals['name'] = body['name']
    if body.get('description') is not None:
        vals['description'] = body['description']
    if body.get('required_level') is not None:
        vals['required_level'] = int(body['required_level'])
    if body.get('is_active') is not None:
        val = body['is_active']
        vals['is_active'] = bool(val) if isinstance(val, (bool, int)) else str(val) in ('1', 'true', 'True')

    if not vals:
        return fail("没有要更新的字段")

    await db.execute(
        update(VIPFeature).where(VIPFeature.id == feature_id).values(**vals)
    )
    await db.flush()
    return ok(data={"message": "更新成功"})


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
        return fail("功能不存�?)
    await db.delete(feature)
    await db.commit()
    return ok(data={"message": "已删�?})


@router.get("/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(admin_required_api)):
    """
    管理员面板入�?
    Returns:
    管理员面板信�?    """
    return {
        'success': True,
        'message': '管理员面�?,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'is_staff': getattr(current_user, 'is_staff', False),
            'is_superuser': getattr(current_user, 'is_superuser', False)
        }
    }
