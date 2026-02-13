"""
仪表板相关API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.models.article import Article
from src.models.media import Media, FileHash
from src.models.notification import Notification
from src.models.role import Role, UserRole
from src.models.user import User
from src.models.vip import VIPSubscription, VIPPlan

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
        request: Request,
        current_user: User = Depends(jwt_required),
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
        new_users_query = select(func.count()).select_from(User).where(User.created_at >= week_ago)
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
        current_user: User = Depends(jwt_required),
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
        recent_articles_query = select(Article).options(selectinload(Article.author)).order_by(
            desc(Article.created_at)).limit(4)
        recent_articles_result = await db.execute(recent_articles_query)
        recent_articles = recent_articles_result.scalars().all()

        articles_data = []
        for article in recent_articles:
            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "author": getattr(article.author, 'username', 'Unknown') if article.author else 'Unknown',
                "views": getattr(article, 'views', 0),
                "comments": 0,  # 暂时设为0，因为评论模型未定义
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "status": "published" if getattr(article, 'status', 0) == 1 else "draft"  # status为1表示published
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
        current_user: User = Depends(jwt_required),
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
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取博客管理文章列表
    """
    try:
        # 使用SQLAlchemy异步查询语法
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload

        # 构建基础查询，预加载关联的作者和分类信息
        query = select(Article).options(
            selectinload(Article.author),
            selectinload(Article.category)
        )

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
            query = query.where(Article.category_id == category_id)

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
            # 确定文章状态
            article_status = 'draft'
            if article.status == 1:
                article_status = 'published'
            elif article.status == 0:
                article_status = 'draft'
            elif article.status == -1:
                article_status = 'deleted'

            # 获取作者信息
            author_info = None
            if hasattr(article, 'author') and article.author:
                author_info = {
                    "id": getattr(article.author, 'id', article.user_id),
                    "username": getattr(article.author, 'username', 'Unknown'),
                    "email": getattr(article.author, 'email', '')
                }
            else:
                # 如果关系未加载，手动查询作者信息
                from sqlalchemy import select
                from src.models.user import User
                author_query = select(User).where(User.id == article.user_id)
                author_result = await db.execute(author_query)
                author = author_result.scalar_one_or_none()
                author_info = {
                    "id": author.id if author else article.user_id,
                    "username": getattr(author, 'username', 'Unknown') if author else 'Unknown',
                    "email": getattr(author, 'email', '') if author else ''
                }

            # 获取分类信息
            category_info = None
            if hasattr(article, 'category') and article.category:
                category_info = {
                    "id": getattr(article.category, 'id', None),
                    "name": getattr(article.category, 'name', ''),
                    "description": getattr(article.category, 'description', '')
                }
            else:
                # 如果关系未加载，手动查询分类信息
                if article.category_id:
                    from sqlalchemy import select
                    from src.models.category import Category
                    category_query = select(Category).where(Category.id == article.category_id)
                    category_result = await db.execute(category_query)
                    category = category_result.scalar_one_or_none()
                    if category:
                        category_info = {
                            "id": category.id,
                            "name": category.name,
                            "description": category.description
                        }

            # 处理标签
            tags_list = []
            if article.tags:
                if isinstance(article.tags, str):
                    tags_list = [tag.strip() for tag in article.tags.split(';') if tag.strip()]
                else:
                    tags_list = article.tags

            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "excerpt": article.excerpt or '',
                "summary": article.excerpt or '',  # summary 通常是 excerpt 的别名
                "cover_image": article.cover_image,
                "tags": tags_list,
                "views": getattr(article, 'views', 0),
                "views_count": getattr(article, 'views', 0),  # 与前端期望的字段一致
                "likes": getattr(article, 'likes', 0),
                "status": article_status,
                "hidden": getattr(article, 'hidden', False),
                "is_vip_only": getattr(article, 'is_vip_only', False),
                "required_vip_level": getattr(article, 'required_vip_level', 0),
                "article_ad": getattr(article, 'article_ad', ''),
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at),
                "user_id": article.user_id,
                "category_id": article.category_id,
                "is_featured": getattr(article, 'is_featured', False),
                "content": getattr(article, 'content', None),  # 可能需要单独获取内容
                "author": author_info,
                "category": category_info,
                "slug": getattr(article, 'slug', f'article-{article.article_id}')  # 确保有slug字段
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
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我的文章列表
    """
    try:
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload

        # 构建基础查询，预加载关联的作者信息
        query = select(Article).options(selectinload(Article.author)).join(User, Article.user_id == User.id).where(
            Article.user_id == current_user.id)

        # 根据状态过滤
        if status:
            # 转换为小写以匹配映射
            status_lower = status.lower()
            status_map = {'published': 1, 'draft': 0, 'deleted': -1}
            if status_lower in status_map:
                query = query.where(Article.status == status_map[status_lower])

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
            # 确定文章状态
            article_status = 'draft'
            if article.status == 1:
                article_status = 'published'
            elif article.status == 0:
                article_status = 'draft'
            elif article.status == -1:
                article_status = 'deleted'

            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "excerpt": article.excerpt or '',
                "cover_image": article.cover_image,
                "category_id": article.category_id,
                "user_id": article.user_id,
                "views": getattr(article, 'views', 0),
                "likes": getattr(article, 'likes', 0),
                "tags": article.tags.split(';') if article.tags else [],
                "status": article.status,
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at),
                "slug": article.slug,
                "author": {
                    "id": article.author.id if article.author else article.user_id,
                    "username": article.author.username if article.author else '未知作者'
                },
                "comments": 0  # 暂时设为0，因为评论模型未定义
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
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取媒体管理文件列表
    """
    try:
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload

        # 查询媒体文件，按用户过滤
        query = select(Media).options(selectinload(Media.file_hash)).where(Media.user_id == current_user.id)

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
async def get_user_management_users(
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        role: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户管理用户列表
    """
    try:
        from sqlalchemy import select
        query = select(User)

        # 根据角色过滤
        if role:
            # 通过UserRole关联表查找具有特定角色的用户
            from sqlalchemy import select
            role_query = select(Role).where(Role.name == role)
            role_result = await db.execute(role_query)
            role_obj = role_result.scalar_one_or_none()
            if role_obj:
                query = query.join(UserRole).filter(UserRole.role_id == role_obj.id)

        # 根据搜索词过滤
        if search:
            query = query.filter(
                User.username.contains(search) | User.email.contains(search)
            )

        # 分页
        offset = (page - 1) * per_page
        from sqlalchemy.orm import selectinload
        users_query = select(User).options(selectinload(User.roles))

        # 根据角色过滤
        if role:
            role_query = select(Role).where(Role.name == role)
            role_result = await db.execute(role_query)
            role_obj = role_result.scalar_one_or_none()
            if role_obj:
                users_query = users_query.join(UserRole).where(UserRole.role_id == role_obj.id)

        # 根据搜索词过滤
        if search:
            users_query = users_query.where(
                User.username.contains(search) | User.email.contains(search)
            )

        # 获取总数
        total_query = select(func.count()).select_from(users_query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 获取用户数据
        users_result = await db.execute(
            users_query.offset(offset).limit(per_page)
        )
        users = users_result.scalars().all()

        users_data = []
        for user in users:
            # 确定用户角色
            user_roles = [ur.name for ur in user.roles] if user.roles else []
            user_role = user_roles[0] if user_roles else "user"  # 默认为普通用户

            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user_role,
                "status": "active" if user.is_active else "inactive",
                "join_date": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                "last_active": getattr(user, 'last_login_at', None)
            })

        return ApiResponse(
            success=True,
            data=users_data,
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


@router.get("/role-management/roles")
async def get_role_management_roles(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取角色管理角色列表
    """
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from datetime import datetime

        # 查询所有角色及其权限
        roles_query = select(Role).options(selectinload(Role.permissions))
        roles_result = await db.execute(roles_query)
        roles = roles_result.scalars().all()

        roles_data = []
        for role in roles:
            permissions = [{
                "id": perm.id,
                "code": perm.code,
                "description": perm.description
            } for perm in role.permissions]

            roles_data.append({
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": permissions,
                "created_at": role.created_at.isoformat() if hasattr(role,
                                                                     'created_at') and role.created_at else datetime.now().isoformat()
            })

        return ApiResponse(
            success=True,
            data=roles_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/system-settings")
async def get_system_settings(
        request: Request,
        current_user: User = Depends(jwt_required),
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
        current_user: User = Depends(jwt_required),
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
        current_user: User = Depends(jwt_required),
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
        total_articles_query = select(func.count(Article.article_id))
        total_articles_result = await db.execute(total_articles_query)
        total_articles = total_articles_result.scalar()

        # 计算已发布文章数
        from sqlalchemy import select
        published_articles_query = select(func.count(Article.article_id)).where(Article.status == 1)
        published_articles_result = await db.execute(published_articles_query)
        published_articles = published_articles_result.scalar()

        # 计算草稿文章数
        from sqlalchemy import select
        draft_articles_query = select(func.count(Article.article_id)).where(Article.status == 0)
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
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")

        # 检查权限 - 只有超级用户或文章作者可以删除
        if not current_user.is_superuser and article.user_id != current_user.id:
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
