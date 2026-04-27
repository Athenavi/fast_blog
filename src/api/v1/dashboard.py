"""
仪表板相关 API
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import desc
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import VIPPlan
from shared.models.article import Article
from shared.models.category import Category
from shared.models.file_hash import FileHash
from shared.models.media import Media
from shared.models.notification import Notification
from shared.models.user import User
# 导入 SQLAlchemy 模型和服务
from shared.models.user import User as UserModel
from shared.models.vip_subscription import VIPSubscription
# 注意：避免在此处直接导入 article_service，防止循环依赖
# article_service 的导入已移至使用位置
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import _get_current_active_user
from src.auth.auth_deps import admin_required_api, jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取仪表板统计数据
    """
    try:
        from sqlalchemy import select, func
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

        return ApiResponse(
            success=True,
            data=stats_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/dashboard/recent-articles")
async def __get_recent_articles(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取最近的文章
    """
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from sqlalchemy import desc

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

        return ApiResponse(
            success=True,
            data=articles_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/dashboard/traffic")
async def get_traffic_data(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取流量数据
    """
    try:
        from sqlalchemy import select, func
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

        return ApiResponse(
            success=True,
            data=traffic_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/blog-management/articles")
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
    try:
        # 使用SQLAlchemy异步查询语法
        from sqlalchemy import select, func

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
            from sqlalchemy import select
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

            # 处理标签（将 tags_list 字符串转换为数组）
            tags_list = []
            if article_dict.get('tags_list'):
                if isinstance(article_dict['tags_list'], str):
                    tags_list = [tag.strip() for tag in article_dict['tags_list'].split(';') if tag.strip()]
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

        return ApiResponse(
            success=True,
            data=articles_data,
            pagination={
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page < (total + per_page - 1) // per_page,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_blog_management_articles: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/my/articles")
async def get_my_articles(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        status: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        hidden: Optional[bool] = Query(None),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我的文章列表
    """
    try:
        from sqlalchemy import select, func, or_
        from sqlalchemy.orm import selectinload

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
        
        # 搜索功能
        if search:
            query = query.where(
                or_(
                    Article.title.contains(search),
                    Article.excerpt.contains(search)
                )
            )

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

            # 处理标签（将 tags_list 字符串转换为数组）
            tags_list = []
            if article_dict.get('tags_list'):
                if isinstance(article_dict['tags_list'], str):
                    tags_list = [tag.strip() for tag in article_dict['tags_list'].split(';') if tag.strip()]
                else:
                    tags_list = article_dict['tags_list']

            # 检查文章是否有密码保护
            has_password = False
            try:
                from sqlalchemy import select
                from shared.models.article_content import ArticleContent
                content_query = select(ArticleContent).where(ArticleContent.article == article.id)
                content_result = await db.execute(content_query)
                content = content_result.scalar_one_or_none()
                has_password = bool(content and content.passwd)
            except Exception as e:
                print(f"检查文章密码状态失败: {e}")

            articles_data.append({
                **article_dict,  # 展开模型的基础字段
                "summary": article_dict.get('excerpt', ''),  # 前端期望的字段名
                "tags": tags_list,  # 转换后的标签数组
                "status": article_status,  # 覆盖为字符串状态
                "has_password": has_password,  # 添加密码保护状态
                "author": {
                    "id": article.user,
                    "username": "未知作者"  # 由于 author 关系已注释，暂时显示未知
                },
                "comments": 0  # 暂时设为 0，因为评论模型未定义
            })

        return ApiResponse(
            success=True,
            data=articles_data,
            pagination={
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page < (total + per_page - 1) // per_page,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/my/messages")
async def get_my_messages(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我的消息列表
    返回收件箱、已发送和通知三种类型的消息
    """
    try:
        from sqlalchemy import select

        # 获取用户的所有通知
        notifications_query = select(Notification).where(
            Notification.recipient_id == current_user.id
        ).order_by(desc(Notification.created_at))
        notifications_result = await db.execute(notifications_query)
        notifications = notifications_result.scalars().all()

        # 转换通知数据为前端期望的格式
        notification_list = []
        for notif in notifications:
            notification_list.append({
                "id": notif.id,
                "title": notif.title,
                "content": notif.message,
                "date": notif.created_at.isoformat(),
                "type": notif.type,
                "read": notif.is_read,
                "avatar": f"/avatars/{current_user.username}.jpg",  # 使用用户头像
                "sender": "System",  # 系统通知
                "recipient": current_user.username
            })

        return ApiResponse(
            success=True,
            data=notification_list
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/media-management/files")
async def get_media_management_files(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        file_type: Optional[str] = Query(None, alias="type"),
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取媒体管理文件列表
    """
    try:
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload

        # 查询媒体文件，按用户过滤
        query = select(Media).options(selectinload(Media.hash)).where(Media.user == current_user.id)

        # 根据文件类型过滤
        if file_type:
            if file_type == 'images':
                query = query.join(FileHash).where(FileHash.mime_type.like('image/%'))
            elif file_type == 'documents':
                query = query.join(FileHash).where(FileHash.mime_type.in_([
                    'application/pdf', 'application/msword', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint'
                ]))
            elif file_type == 'videos':
                query = query.join(FileHash).where(FileHash.mime_type.like('video/%'))

        # 计算总数
        total_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 分页查询
        offset = (page - 1) * per_page
        media_files_query = query.offset(offset).limit(per_page)
        media_files_result = await db.execute(media_files_query)
        media_files = media_files_result.scalars().all()

        # 转换文件数据
        files_data = []
        for media in media_files:
            # 获取文件类型
            file_ext = media.original_filename.split('.')[-1].lower() if '.' in media.original_filename else ''
            file_type = 'document'
            if media.file_hash.mime_type.startswith('image/'):
                file_type = 'image'
            elif media.file_hash.mime_type.startswith('video/'):
                file_type = 'video'
            elif file_ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf']:
                file_type = 'document'
            elif file_ext in ['mp3', 'wav', 'ogg', 'flac']:
                file_type = 'audio'

            files_data.append({
                "id": media.id,
                "name": media.original_filename,
                "url": f"/media/{media.file_hash.storage_path}/{media.original_filename}",
                "size": media.file_hash.file_size,
                "upload_date": media.created_at.isoformat(),
                "type": file_type,
                "extension": file_ext,
                "mime_type": media.file_hash.mime_type
            })

        return ApiResponse(
            success=True,
            data={
                "media_items": [{
                    "id": item["id"],
                    "original_filename": item["name"],
                    "hash": "",  # 在管理界面中可能不需要hash
                    "mime_type": item["mime_type"],
                    "file_size": item["size"],
                    "created_at": item["upload_date"]
                } for item in files_data],
                "users": [],
                "pagination": {
                    "current_page": page,
                    "pages": (total + per_page - 1) // per_page,
                    "total": total,
                    "has_prev": page > 1,
                    "has_next": page < (total + per_page - 1) // per_page,
                    "per_page": per_page
                }
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/user-management/users")
async def get_users(
        request: Request,
        current_user: UserModel = Depends(_get_current_active_user),
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        search: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_async_db)
):
    """获取所有用户信息（管理员专用）"""
    try:
        # 检查管理员权限
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(status_code=403, detail="权限不足")

        # 构建查询条件
        base_query = select(UserModel)
        if search:
            base_query = base_query.where(
                UserModel.username.contains(search) | UserModel.email.contains(search)
            )

        # 获取总数
        total_query = select(func.count()).select_from(UserModel)
        if search:
            total_query = total_query.where(
                UserModel.username.contains(search) | UserModel.email.contains(search)
            )
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 获取分页数据
        offset = (page - 1) * per_page
        users_query = base_query.offset(offset).limit(per_page)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()

        # 构建响应数据
        users_data = []
        for user in users:
            # 查询用户的角色
            from shared.models.user_role import UserRole
            from shared.models.role import Role
            import json

            roles_query = select(Role).join(
                UserRole, Role.id == UserRole.role_id
            ).where(
                UserRole.user_id == user.id
            )
            roles_result = await db.execute(roles_query)
            user_roles = roles_result.scalars().all()

            print(f"DEBUG: User {user.username} (ID: {user.id}) has {len(user_roles)} roles")

            # 构建角色数据
            roles_data = []
            for role in user_roles:
                # 解析权限列表
                try:
                    permissions_list = json.loads(role.permissions) if role.permissions else []
                except Exception as e:
                    print(f"DEBUG: Error parsing permissions for role {role.id}: {e}")
                    permissions_list = []

                print(f"DEBUG: Role {role.name} (ID: {role.id}) has permissions: {permissions_list}")

                roles_data.append({
                    "id": role.id,
                    "name": role.name,
                    "slug": role.slug,
                    "description": role.description or "",
                    "permissions": permissions_list  # 添加权限列表
                })

            print(f"DEBUG: User {user.username} roles_data: {roles_data}")

            # 这里可以添加计算用户存储使用量的逻辑
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "bio": user.bio,
                "profile_picture": user.profile_picture,
                "created_at": user.date_joined.isoformat() if user.date_joined else None,
                "last_login": getattr(user, 'last_login', None),
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "storage_used": 0,  # 占位符，实际应计算存储使用量
                "roles": roles_data  # 添加角色信息
            })

        return ApiResponse(
            success=True,
            data={
                "users": users_data,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": page < (total + per_page - 1) // per_page,
                    "has_prev": page > 1
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        return ApiResponse(success=False, error=f"获取用户列表失败: {str(e)}")


@router.get("/system-settings")
async def get_system_settings(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取系统设置
    """
    try:
        # 返回系统设置数据
        # 注意：实际应用中这些设置通常存储在配置表中
        settings_data = {
            "general": {
                "site_name": "FastBlog",
                "site_description": "一个快速的博客系统",
                "site_url": "http://localhost:3000",
                "default_language": "zh-CN"
            },
            "security": {
                "max_login_attempts": 5,
                "session_timeout": 120,  # 分钟
                "enable_two_factor_auth": False
            },
            "email": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",  # 实际应用中不会返回密码
                "from_email": "noreply@example.com"
            }
        }

        return ApiResponse(
            success=True,
            data=settings_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/system-settings")
async def update_system_settings(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新系统设置
    """
    try:
        data = await request.json()
        # 在实际实现中，需要验证和保存设置到数据库
        # 这里只是示例，实际应用中应将设置保存到系统配置表中

        return ApiResponse(
            success=True,
            data={"message": "System settings updated successfully"}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/vip-management")
async def get_vip_management_data(
        request: Request,
        current_user: User = Depends(admin_required_api),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取VIP管理数据
    """
    try:
        # 查询VIP订阅数据
        from sqlalchemy import select
        subscriptions_query = select(VIPSubscription).join(VIPPlan)
        subscriptions_result = await db.execute(subscriptions_query)
        subscriptions = subscriptions_result.scalars().all()
        subscriptions_data = []
        for sub in subscriptions:
            subscriptions_data.append({
                "id": sub.id,
                "user_id": sub.user_id,
                "user_name": sub.user.username if sub.user else "Unknown User",
                "plan_name": sub.plan.name if sub.plan else "Unknown Plan",
                "start_date": sub.starts_at.isoformat() if sub.starts_at else None,
                "end_date": sub.expires_at.isoformat() if sub.expires_at else None,
                "status": "active" if sub.status == 1 else "inactive",
                "amount": float(sub.payment_amount) if sub.payment_amount else 0.00
            })

        # 查询VIP计划数据
        from sqlalchemy import select
        plans_query = select(VIPPlan)
        plans_result = await db.execute(plans_query)
        plans = plans_result.scalars().all()
        premium_content = []
        for plan in plans:
            premium_content.append({
                "id": plan.id,
                "title": plan.name,
                "author": "System",  # 这里可以是管理员或者特定作者
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "status": "published" if plan.is_active else "inactive",
                "views": 0  # 这里可以是VIP内容的浏览量
            })

        vip_data = {
            "subscriptions": subscriptions_data,
            "premium_content": premium_content
        }

        return ApiResponse(
            success=True,
            data=vip_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/blog-management/articles/stats")
async def get_blog_management_articles_stats(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取博客管理文章统计信息
    """
    try:
        # 计算文章总数
        from sqlalchemy import select
        total_articles_query = select(func.count(Article.id))
        total_articles_result = await db.execute(total_articles_query)
        total_articles = total_articles_result.scalar()

        # 计算已发布文章数
        from sqlalchemy import select
        published_articles_query = select(func.count(Article.id)).where(Article.status == 1)
        published_articles_result = await db.execute(published_articles_query)
        published_articles = published_articles_result.scalar()

        # 计算草稿文章数
        from sqlalchemy import select
        draft_articles_query = select(func.count(Article.id)).where(Article.status == 0)
        draft_articles_result = await db.execute(draft_articles_query)
        draft_articles = draft_articles_result.scalar()

        # 计算总浏览量
        from sqlalchemy import select
        total_views_query = select(func.sum(Article.views))
        total_views_result = await db.execute(total_views_query)
        total_views = total_views_result.scalar() or 0

        stats_data = {
            "total_articles": total_articles,
            "published_articles": published_articles,
            "draft_articles": draft_articles,
            "total_views": total_views
        }

        return ApiResponse(
            success=True,
            data=stats_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/blog-management/articles/{article_id}")
async def delete_blog_management_article(
        request: Request,
        article_id: int,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除博客管理文章
    """
    try:
        from sqlalchemy import select
        article_query = select(Article).where(Article.id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")

        # 检查权限 - 只有超级用户或文章作者可以删除
        if not current_user.is_superuser and article.user != current_user.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")

        await db.delete(article)
        await db.commit()

        return ApiResponse(
            success=True,
            data={"message": "Article deleted successfully"}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
