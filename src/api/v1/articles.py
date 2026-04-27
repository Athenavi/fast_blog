"""
文章相关API
"""
from datetime import datetime
from typing import Optional

from django.contrib.auth.backends import UserModel
from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.models.article_content import ArticleContent
from shared.models.category import Category
from shared.models.user import User
from shared.services.article_manager import article_query_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required, jwt_optional_dependency
from src.utils.database.main import get_async_session
from src.utils.filters import md2html

router = APIRouter()


@router.get("",
            summary="获取文章列表",
            description="""
获取分页的文章列表，支持多种筛选和搜索功能。

**功能特性**:
- 分页支持 (page, per_page)
- 关键词搜索 (search) - 搜索标题和摘要
- 分类筛选 (category_id)
- 作者筛选 (user_id)  
- 状态筛选 (status: draft/published/deleted)
- **粘性文章优先排序** - 置顶文章自动排在前面

**使用场景**:
- 首页文章展示
- 分类页面文章列表
- 用户个人文章列表
- 管理后台文章管理
            """,
            response_description="返回文章列表和分页信息",
            responses={
                200: {
                    "description": "成功获取文章列表",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "data": [
                                    {
                                        "id": 1,
                                        "title": "FastAPI 入门教程",
                                        "slug": "fastapi-intro",
                                        "excerpt": "本文介绍 FastAPI 的基本用法...",
                                        "cover_image": "/media/covers/fastapi.jpg",
                                        "tags": ["Python", "FastAPI", "后端"],
                                        "author": {"id": 1, "username": "admin"},
                                        "category_id": 1,
                                        "category_name": "技术教程",
                                        "views": 1234,
                                        "likes": 56,
                                        "status": 1,
                                        "created_at": "2026-04-01T10:00:00",
                                        "updated_at": "2026-04-09T15:30:00"
                                    }
                                ],
                                "pagination": {
                                    "current_page": 1,
                                    "per_page": 10,
                                    "total": 100,
                                    "total_pages": 10,
                                    "has_next": True,
                                    "has_prev": False
                                }
                            }
                        }
                    }
                }
            })
async def get_articles_api(
        request: Request,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100之间"),
        search: str = Query("", description="搜索关键词，用于标题和摘要搜索"),
        category_id: Optional[int] = Query(None, description="分类ID，用于筛选特定分类的文章"),
        user_id: Optional[int] = Query(None, description="用户ID，用于筛选特定用户的文章"),
        status: Optional[str] = Query(None, description="状态筛选，可选值: draft, published, deleted"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取文章列表API（支持粘性文章优先排序）
    """
    try:
        # 检查是否为管理员
        is_admin = False
        # 安全地检查用户认证状态，直接检查 scope 避免触发 Starlette 的断言
        if 'user' in request.scope and request.scope['user'] is not None:
            user = request.scope['user']
            try:
                is_admin = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
            except Exception:
                # 如果访问 user 属性失败，默认为非管理员
                is_admin = False

        print(f'\n🔍 [DEBUG] get_articles_api called')
        print(f'   - page: {page}, per_page: {per_page}')
        print(f'   - search: {search}')
        print(f'   - category_id: {category_id}')
        print(f'   - user_id: {user_id}')
        print(f'   - status: {status}')
        print(f'   - is_admin: {is_admin}')

        # 使用查询服务获取文章列表（自动处理粘性文章排序）
        articles, total = await article_query_service.get_articles_list(
            db=db,
            page=page,
            per_page=per_page,
            search=search if search else None,
            category_id=category_id,
            user_id=user_id,
            status=status,
            include_sticky=True,
            is_admin=is_admin
        )

        print(f'   - Found {len(articles)} articles, total: {total}')

        # 批量加载作者信息，避免 N+1 查询
        user_ids = [article.user for article in articles if article.user]
        users_dict = {}
        if user_ids:
            users_query = select(User).where(User.id.in_(user_ids))
            users_result = await db.execute(users_query)
            for user in users_result.scalars().all():
                users_dict[user.id] = user

        # 批量加载分类信息，避免 N+1 查询
        category_ids = [article.category for article in articles if article.category]
        categories_dict = {}
        if category_ids:
            categories_query = select(Category).where(Category.id.in_(category_ids))
            categories_result = await db.execute(categories_query)
            for category in categories_result.scalars().all():
                categories_dict[category.id] = category

        # 构建响应数据
        articles_data = []
        for article in articles:
            articles_data.append({
                "id": article.id,
                "title": article.title,
                "slug": article.slug,  # 添加 slug 字段
                "excerpt": article.excerpt,
                "content": getattr(article, 'content', None),  # 如果有内容的话
                "cover_image": article.cover_image or None,  # 添加封面图片字段
                "tags": article.tags_list or None,  # 添加标签字段
                "author": {
                    "id": article.user,
                    "username": users_dict.get(article.user,
                                               User(username="Unknown")).username if users_dict else "Unknown"
                },
                "category_id": article.category,
                "category_name": categories_dict.get(
                    article.category).name if article.category and categories_dict else None,
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at) if article.created_at else None,
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at) if article.updated_at else None
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
        print(f"Error in get_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/detail",
            summary="获取文章详情(通过查询参数)",
            description="通过查询参数 id 获取指定文章的详细信息，并增加浏览量",
            response_description="返回文章详细信息")
async def get_article_detail_by_query_api(
        request: Request,
        id: int = Query(..., description="文章ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    通过查询参数获取文章详情API
    """
    try:
        # 正确加载文章及其作者信息
        article_query = select(Article).where(
            Article.id == id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 增加浏览量
        article.views = (article.views or 0) + 1
        await db.commit()

        # 获取文章内容
        article_content_query = select(ArticleContent).where(ArticleContent.article == article.id)
        article_content_result = await db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        content = article_content.content if article_content else ""

        # 将Markdown内容转换为HTML
        if content:
            content = md2html(content)

            # 解析Shortcode
            from shared.services.shortcode_service import shortcode_service
            content = shortcode_service.parse(content)

        # 单独获取作者信息
        author_query = select(User).where(User.id == article.user)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 构建作者信息，确保不为 None
        author_info = {
            "id": article.user,
            "username": getattr(author, 'username', "Unknown") if author else "Unknown",
            "bio": getattr(author, 'bio', "") if author else "",
            "profile_picture": getattr(author, 'profile_picture', None) if author else None
        }

        article_data = {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": content,
            "author": author_info,
            "category_id": article.category,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "is_sticky": getattr(article, 'is_sticky', False),
            "sticky_until": article.sticky_until.isoformat() if hasattr(article,
                                                                        'sticky_until') and article.sticky_until else None,
            "created_at": article.created_at.isoformat() if article.created_at else str(article.created_at),
            "updated_at": article.updated_at.isoformat() if article.updated_at else str(article.updated_at)
        }

        return ApiResponse(success=True, data=article_data)
    except Exception as e:
        import traceback
        print(f"Error in get_article_detail_by_query_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/{article_id}",
            summary="获取文章详情",
            description="获取指定文章的详细信息，并增加浏览量",
            response_description="返回文章详细信息")
async def get_article_detail_api(
        request: Request,
        article_id: int,
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取文章详情API
    """
    try:
        # 正确加载文章及其作者信息
        article_query = select(Article).where(
            Article.id == article_id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 增加浏览量
        article.views = (article.views or 0) + 1
        await db.commit()

        # 触发页面访问事件
        try:
            import asyncio
            from shared.services.plugin_manager import trigger_plugin_event

            # 检查是否有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(trigger_plugin_event('page_view', {
                    'url': f'/articles/{article_id}',
                    'title': article.title,
                    'article_id': article_id,
                    'user_id': request.state.current_user,
                    'ip': request.client.host if request.client else None,
                    'referrer': request.headers.get('referer'),
                    'user_agent': request.headers.get('user-agent'),
                }))
            except RuntimeError:
                # 没有运行的事件循环，跳过事件触发
                pass
        except Exception as e:
            print(f"[Plugin] Failed to trigger page_view event: {e}")

        # 获取文章内容
        article_content_query = select(ArticleContent).where(ArticleContent.article == article_id)
        article_content_result = await db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        content = article_content.content if article_content else ""

        # 将Markdown内容转换为HTML
        if content:
            content = md2html(content)

            # 解析Shortcode
            from shared.services.shortcode_service import shortcode_service
            content = shortcode_service.parse(content)

        # 单独获取作者信息
        author_query = select(User).where(User.id == article.user)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 构建作者信息，确保不为 None
        author_info = {
            "id": article.user,
            "username": getattr(author, 'username', "Unknown") if author else "Unknown",
            "bio": getattr(author, 'bio', "") if author else "",
            "profile_picture": getattr(author, 'profile_picture', None) if author else None
        }

        article_data = {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": content,
            "author": author_info,
            "category_id": article.category,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "is_sticky": getattr(article, 'is_sticky', False),
            "sticky_until": article.sticky_until.isoformat() if hasattr(article,
                                                                        'sticky_until') and article.sticky_until else None,
            "created_at": article.created_at.isoformat() if article.created_at else str(article.created_at),
            "updated_at": article.updated_at.isoformat() if article.updated_at else str(article.updated_at)
        }

        return ApiResponse(success=True, data=article_data)
    except Exception as e:
        import traceback
        print(f"Error in get_article_detail_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/{article_id}/raw",
            summary="获取文章原始内容",
            description="获取文章的原始 Markdown 格式内容，用于编辑页面",
            response_description="返回文章原始内容，不进行 HTML 渲染")
async def get_article_raw_content_api(
        request: Request,
        article_id: int,
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取文章原始内容 API（不进行 HTML 渲染）
    专门用于编辑页面，返回原始 Markdown 格式内容
    """
    try:
        # 加载文章及其作者信息
        article_query = select(Article).where(
            Article.id == article_id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 获取文章原始内容（不进行渲染）
        article_content_query = select(ArticleContent).where(ArticleContent.article == article_id)
        article_content_result = await db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        raw_content = article_content.content if article_content else ""

        # 获取作者信息
        author_query = select(User).where(User.id == article.user)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 构建作者信息
        author_info = {
            "id": article.user,
            "username": getattr(author, 'username', "Unknown") if author else "Unknown",
            "bio": getattr(author, 'bio', "") if author else "",
            "profile_picture": getattr(author, 'profile_picture', None) if author else None
        }

        article_data = {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": raw_content,  # 返回原始内容，不进行渲染
            "author": author_info,
            "category_id": article.category,
            "cover_image": article.cover_image,
            "tags": article.tags_list,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "hidden": article.hidden,
            "is_vip_only": article.is_vip_only,
            "required_vip_level": article.required_vip_level,
            "is_sticky": getattr(article, 'is_sticky', False),
            "sticky_until": article.sticky_until.isoformat() if hasattr(article,
                                                                        'sticky_until') and article.sticky_until else None,
            "created_at": article.created_at.isoformat() if article.created_at else str(article.created_at),
            "updated_at": article.updated_at.isoformat() if article.updated_at else str(article.updated_at)
        }

        return ApiResponse(success=True, data=article_data)
    except Exception as e:
        import traceback
        print(f"Error in get_article_raw_content_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("",
             summary="创建文章",
             description="创建新文章，需要用户认证",
             response_description="返回创建的文章 ID 和消息")
async def create_article_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """
    创建文章API
    """
    try:
        # 获取表单数据
        form_data = await request.form()

        from datetime import datetime

        # 处理slug，如果为空则根据标题生成
        slug = form_data.get('slug', '')
        if not slug or slug.strip() == '':
            # 如果slug为空，根据标题生成
            title = form_data.get('title', '')
            if title:
                # 使用更严格的slug化处理
                import re
                slug = re.sub(r'[\s\u3000]+', '-', title.lower().strip())  # 替换空格为连字符
                slug = re.sub(r'[^\w\-]+', '-', slug)  # 替换非单词字符为连字符
                slug = re.sub(r'-+', '-', slug)  # 将多个连字符替换为单个
                slug = slug.strip('-')  # 删除开头和结尾的连字符

                # 确保slug不重复
                original_slug = slug
                counter = 1
                while True:
                    from sqlalchemy import select
                    existing_article_query = select(Article).where(Article.slug == slug)
                    existing_article_result = await db.execute(existing_article_query)
                    existing_article = existing_article_result.scalar_one_or_none()
                    if not existing_article:
                        break
                    slug = f"{original_slug}-{counter}"
                    counter += 1

        # 处理 tags，将列表转换为分号分隔的字符串
        tags = form_data.get('tags', '')
        if isinstance(tags, list):
            tags_str = ';'.join(tags)
        elif isinstance(tags, str):
            tags_str = tags
        else:
            tags_str = ''

        new_article = Article(
            title=form_data.get('title', ''),
            slug=slug,
            user=current_user.id,  # 当前用户为作者
            excerpt=form_data.get('excerpt', ''),
            cover_image=form_data.get('cover_image', ''),
            tags_list=tags_str,
            status=int(form_data.get('status', 0)) if form_data.get('status', '0').isdigit() else 0,
            hidden=form_data.get('hidden') is not None,
            is_vip_only=form_data.get('is_vip_only') is not None,
            required_vip_level=int(form_data.get('required_vip_level', 0)) if form_data.get('required_vip_level',
                                                                                            '0').isdigit() else 0,
            is_featured=form_data.get('is_featured') is not None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 处理定时发布时间
        scheduled_publish_at = form_data.get('scheduled_publish_at', '')
        if scheduled_publish_at and scheduled_publish_at.strip():
            try:
                from datetime import timezone
                # 解析ISO格式的时间字符串
                new_article.scheduled_publish_at = datetime.fromisoformat(scheduled_publish_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                print(f"解析定时发布时间失败: {e}")

        # 处理分类
        try:
            category_id = form_data.get('category_id')
            if category_id and category_id != 'None' and category_id != '':
                new_article.category = int(category_id)
        except ValueError:
            pass  # 如果分类ID无效，保持为None

        db.add(new_article)
        await db.flush()  # 获取新文章的 ID

        # 创建文章内容
        content_text = form_data.get('content', '')
        now = datetime.now()
        new_content = ArticleContent(
            article=new_article.id,
            content=content_text,
            created_at=now,
            updated_at=now
        )
        db.add(new_content)

        try:
            await db.commit()
            return ApiResponse(
                success=True,
                data={
                    "message": "Article created successfully",
                    "article_id": new_article.id
                }
            )
        except Exception as e:
            await db.rollback()
            return ApiResponse(success=False, error=f"创建文章失败: {str(e)}", data=None)
    except Exception as e:
        import traceback
        print(f"Error in create_article_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.put("/{article_id}",
            summary="更新文章",
            description="更新指定文章的信息，只有文章作者可以更新",
            response_description="返回更新结果消息")
async def update_article_api(
        request: Request,
        article_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """
    更新文章API
    """
    try:
        # 检查权限 - 只有作者或管理员可以编辑
        from sqlalchemy import select
        article_query = select(Article).where(Article.id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")
        current_user_query = select(UserModel).where(UserModel.id == current_user.id)
        current_user_result = await db.execute(current_user_query)
        current_user_db = current_user_result.scalar_one_or_none()

        # 检查是否是文章作者或者是否具有管理员权限
        is_author = article.user == current_user.id
        is_admin = current_user_db and hasattr(current_user_db, 'is_admin') and current_user_db.is_admin

        if not (is_author or is_admin):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")

        # 获取表单数据
        form_data = await request.form()

        # 更新文章基本字段
        article.title = form_data.get('title', '')

        # 处理slug，如果为空则根据标题生成
        slug = form_data.get('slug', '')
        if not slug or slug.strip() == '':
            # 如果slug为空，根据标题生成
            title = form_data.get('title', '')
            if title and title.strip():  # 确保标题不为空
                # 使用更严格的slug化处理
                import re
                slug = re.sub(r'[\s\u3000]+', '-', title.lower().strip())  # 替换空格为连字符
                slug = re.sub(r'[^\w\-]+', '-', slug)  # 替换非单词字符为连字符
                slug = re.sub(r'-+', '-', slug)  # 将多个连字符替换为单个
                slug = slug.strip('-')  # 删除开头和结尾的连字符

                # 确保slug不重复
                original_slug = slug
                counter = 1
                while True:
                    from sqlalchemy import select
                    existing_article_query = select(Article).where(
                        Article.slug == slug,
                        Article.id != article_id  # 排除当前文章本身
                    )
                    existing_article_result = await db.execute(existing_article_query)
                    existing_article = existing_article_result.scalar_one_or_none()
                    if not existing_article:
                        break
                    slug = f"{original_slug}-{counter}"
                    counter += 1
            else:
                # 如果标题也为空，使用默认slug
                slug = f"untitled-{article_id}"

        article.slug = slug
        article.excerpt = form_data.get('excerpt', '')
        article.cover_image = form_data.get('cover_image', '')

        # 处理 tags，将列表转换为分号分隔的字符串
        tags = form_data.get('tags', '')
        if isinstance(tags, list):
            article.tags_list = ';'.join(tags)
        elif isinstance(tags, str):
            article.tags_list = tags
        else:
            article.tags_list = ''

        # 处理状态
        status_str = form_data.get('status', '0')
        try:
            article.status = int(status_str)
        except ValueError:
            article.status = 0

        # 处理隐藏设置
        article.hidden = form_data.get('hidden') is not None

        # 处理VIP相关设置
        article.is_vip_only = form_data.get('is_vip_only') is not None
        try:
            article.required_vip_level = int(form_data.get('required_vip_level', 0))
        except ValueError:
            article.required_vip_level = 0

        # 处理特色文章设置
        article.is_featured = form_data.get('is_featured') is not None

        # 处理分类
        try:
            category_id = form_data.get('category_id')
            if category_id and category_id != 'None' and category_id != '':
                article.category = int(category_id)
            else:
                article.category = None
        except ValueError:
            article.category = None

        # 处理定时发布时间
        scheduled_publish_at = form_data.get('scheduled_publish_at', '')
        if scheduled_publish_at and scheduled_publish_at.strip():
            try:
                article.scheduled_publish_at = datetime.now()
            except (ValueError, AttributeError) as e:
                print(f"解析定时发布时间失败: {e}")
        elif scheduled_publish_at == '':
            # 如果传空字符串，清除定时发布
            article.scheduled_publish_at = None

        article.updated_at = datetime.now()

        # 获取文章内容
        content_text = form_data.get('content', '')

        # 更新或创建文章内容
        from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.article == article_id)
        content_result = await db.execute(content_query)
        old_content = content_result.scalar_one_or_none()
        old_content_text = old_content.content if old_content else ""

        # 检查是否有实质性变更（用于决定是否保存修订）
        has_changes = (
                article.title != form_data.get('title', '') or
                old_content_text != content_text or
                article.excerpt != form_data.get('excerpt', '') or
                article.cover_image != form_data.get('cover_image', '') or
                article.tags_list != form_data.get('tags', '')
        )

        if old_content:
            old_content.content = content_text
            old_content.updated_at = datetime.now()
        else:
            now = datetime.now()
            new_content = ArticleContent(
                article=article_id,
                content=content_text,
                created_at=now,
                updated_at=now
            )
            db.add(new_content)

        try:
            await db.commit()

            # 如果有变更，自动保存修订版本
            if has_changes:
                try:
                    from shared.services.article_manager import save_article_revision
                    change_summary = form_data.get('change_summary', '自动保存')
                    await save_article_revision(
                        db=db,
                        article_id=article_id,
                        author_id=current_user.id,
                        change_summary=change_summary
                    )
                except Exception as rev_error:
                    # 修订保存失败不影响主流程
                    print(f"保存修订版本失败: {rev_error}")

            return ApiResponse(
                success=True,
                data={"message": "Article updated successfully"}
            )
        except Exception as e:
            await db.rollback()
            return ApiResponse(success=False, error=f"更新文章失败: {str(e)}", data=None)
    except Exception as e:
        import traceback
        print(f"Error in update_article_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.delete("/{article_id}",
               summary="删除文章",
               description="删除指定文章，只有文章作者可以删除",
               response_description="返回删除结果消息")
async def delete_article_api(
        request: Request,
        article_id: int,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """
    删除文章 API
    """
    try:
        from sqlalchemy import select
        article_query = select(Article).where(Article.id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")

        # 检查权限
        if article.user != current_user.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")

        # 级联删除关联的文章内容
        from shared.models.article_content import ArticleContent
        content_query = select(ArticleContent).where(ArticleContent.article == article.id)
        content_result = await db.execute(content_query)
        content_records = content_result.scalars().all()

        for content in content_records:
            await db.delete(content)

        await db.delete(article)
        await db.commit()

        return ApiResponse(
            success=True,
            data={"message": "Article deleted successfully"}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/user/{user_id}",
            summary="获取用户文章列表",
            description="获取指定用户的文章列表，需要认证",
            response_description="返回用户文章列表和分页信息")
async def get_user_articles_api(
        request: Request,
        user_id: int = Path(..., description="用户 ID"),
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100 之间"),
        current_user: Optional[User] = Depends(jwt_optional_dependency),  # 可选认证
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取指定用户的文章列表API
    """
    try:
        # 检查权限：只能访问自己的文章，或者管理员可以访问任何人的文章
        if current_user:
            # 如果已登录，只能访问自己的文章或管理员访问所有
            if current_user.id != user_id and not getattr(current_user, 'is_superuser', False):
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Permission denied")
        # 如果未登录 (current_user 为 None)，则允许访问公开的用户文章

        # 构建查询 - 只查询指定用户的文章
        from sqlalchemy.orm import selectinload
        query = select(Article).join(User, Article.user == User.id).where(
            Article.user == user_id)

        # 分页
        offset = (page - 1) * per_page
        articles_result = await db.execute(query.order_by(Article.created_at.desc()).offset(offset).limit(per_page))
        articles = articles_result.scalars().all()

        total_query = select(func.count()).select_from(Article).where(Article.user == user_id)
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 构建响应数据
        articles_data = []
        for article in articles:
            # 获取分类信息
            category_name = None
            if article.category:
                category_query = select(Category).where(Category.id == article.category)
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            # 获取标签信息
            tags_list = []
            if article.tags_list:
                tags_list = article.tags_list.split(';')

            articles_data.append({
                "id": article.id,
                "title": article.title,
                "excerpt": article.excerpt,
                "content": getattr(article, 'content', None),
                "author": {
                    "id": article.user,
                    "username": "Unknown"  # 由于 author 关系已注释，暂时显示 Unknown
                },
                "category_id": article.category,
                "category_name": category_name,
                "cover_image": article.cover_image,
                "tags": tags_list,
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "is_vip_only": getattr(article, 'is_vip_only', False),
                "required_vip_level": getattr(article, 'required_vip_level', 0),
                "is_featured": getattr(article, 'is_featured', False),
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at)
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
        print(f"Error in get_user_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/user/{user_id}/stats",
            summary="获取用户统计信息",
            description="获取指定用户的统计信息，包括文章数量、关注者等",
            response_description="返回用户统计信息")
async def get_user_articles_stats_api(
        request: Request,
        user_id: int = Path(..., description="用户 ID"),
        current_user: Optional[User] = Depends(jwt_optional_dependency),  # 可选认证
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取指定用户的统计信息API
    """
    try:
        # 检查权限：只能访问自己的统计信息，或者管理员可以访问任何人的统计信息
        if current_user:
            # 如果已登录，只能访问自己的统计信息或管理员访问所有
            if current_user.id != user_id and not getattr(current_user, 'is_superuser', False):
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Permission denied")
        # 如果未登录 (current_user 为 None)，则允许访问公开的用户统计信息

        # 统计文章数量
        articles_count_query = select(func.count()).select_from(Article).where(Article.user == user_id)
        articles_count_result = await db.execute(articles_count_query)
        articles_count = articles_count_result.scalar()

        # 获取用户关注和粉丝数
        # from src.models.subscription import UserSubscription
        # followers_query = select(func.count()).select_from(UserSubscription).where(UserSubscription.subscribed_user_id == user_id)
        # followers_result = await db.execute(followers_query)
        followers_count = 0

        # following_query = select(func.count()).select_from(UserSubscription).where(UserSubscription.subscriber_id == user_id)
        # following_result = await db.execute(following_query)
        following_count = 0

        stats_data = {
            "articles_count": articles_count,
            "followers_count": followers_count,
            "following_count": following_count
        }

        return ApiResponse(
            success=True,
            data=stats_data
        )
    except Exception as e:
        import traceback
        print(f"Error in get_user_articles_stats_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/home/articles",
            summary="获取首页文章列表",
            description="获取适合在首页展示的文章列表，只返回公开的、非 VIP 的、已发布的文章",
            response_description="返回首页文章列表和分页信息")
async def get_home_articles_api(
        request: Request,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        per_page: int = Query(9, ge=1, le=50, description="每页显示数量，1-50之间"),  # 首页通常显示较少的文章
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取首页文章列表API
    """
    try:
        # 构建查询 - 只获取公开的、非 VIP 的、已发布的文章，并预加载作者信息
        from sqlalchemy.orm import selectinload
        query = select(Article).join(User, Article.user == User.id).where(
            Article.hidden == False,
            Article.status == 1,
            Article.is_vip_only == False
        ).order_by(Article.id.desc())

        # 分页
        offset = (page - 1) * per_page
        articles_result = await db.execute(query.offset(offset).limit(per_page))
        articles = articles_result.scalars().all()

        total_query = select(func.count()).select_from(Article).where(
            Article.hidden == False,
            Article.status == 1,
            Article.is_vip_only == False
        )
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 构建响应数据
        articles_data = []
        for article in articles:
            # 获取分类名称
            category_name = None
            if article.category:
                category_query = select(Category).where(Category.id == article.category)
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            # 处理标签
            tags_list = []
            if article.tags_list:
                tags_list = article.tags_list.split(';')

            articles_data.append({
                "id": article.id,
                "title": article.title,
                "excerpt": article.excerpt,
                "author": {
                    "id": article.user,
                    "username": "Unknown"  # 由于 author 关系已注释，暂时显示 Unknown
                },
                "category_id": article.category,
                "category_name": category_name,
                "cover_image": article.cover_image,
                "tags": tags_list,
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "slug": article.slug,
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at)
            })

        # 返回与前端期望格式一致的数据结构
        return ApiResponse(
            success=True,
            data={
                "data": articles_data,  # 包装在data中
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
    except Exception as e:
        import traceback
        print(f"Error in get_home_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/{article_id}/sticky",
             summary="切换文章粘性状态",
             description="设置或取消文章置顶（粘性），需要管理员权限",
             response_description="返回操作结果")
async def toggle_article_sticky_api(
        request: Request,
        article_id: int = Path(..., description="文章ID"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """
    切换文章粘性状态API（置顶/取消置顶）
    
    只有管理员或文章作者可以操作
    """
    try:
        # 检查权限：仅管理员或文章作者可操作
        if not getattr(current_user, 'is_staff', False) and not getattr(current_user, 'is_superuser', False):
            # 非管理员，检查是否为文章作者
            article_query = select(Article).where(Article.id == article_id)
            article_result = await db.execute(article_query)
            article = article_result.scalar_one_or_none()

            if not article:
                return ApiResponse(success=False, error="Article not found")

            if article.user != current_user.id:
                from fastapi import HTTPException
                raise HTTPException(status_code=403,
                                    detail="Permission denied. Only admin or author can toggle sticky.")

        # 获取请求体数据
        body = await request.json()
        is_sticky = body.get('is_sticky', False)
        sticky_until = body.get('sticky_until', None)

        # 转换 sticky_until 为 datetime 对象
        from datetime import datetime, timezone
        sticky_until_dt = None
        if sticky_until:
            try:
                # 支持 ISO 格式字符串
                if isinstance(sticky_until, str):
                    sticky_until_dt = datetime.fromisoformat(sticky_until.replace('Z', '+00:00'))
                else:
                    sticky_until_dt = sticky_until
            except Exception as e:
                return ApiResponse(success=False, error=f"Invalid sticky_until format: {str(e)}")

        # 使用服务切换粘性状态
        updated_article = await article_query_service.toggle_sticky_status(
            db=db,
            article_id=article_id,
            is_sticky=is_sticky,
            sticky_until=sticky_until_dt
        )

        if not updated_article:
            return ApiResponse(success=False, error="Article not found")

        return ApiResponse(
            success=True,
            data={
                "message": "Sticky status updated successfully",
                "article_id": updated_article.id,
                "is_sticky": updated_article.is_sticky,
                "sticky_until": updated_article.sticky_until.isoformat() if updated_article.sticky_until else None
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in toggle_article_sticky_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/admin/clean-expired-sticky",
             summary="清理过期粘性文章",
             description="自动取消已过期的置顶文章，需要管理员权限",
             response_description="返回清理结果")
async def clean_expired_sticky_articles_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """
    清理过期粘性文章API
    
    只有管理员可以执行此操作
    """
    try:
        # 检查管理员权限
        if not getattr(current_user, 'is_staff', False) and not getattr(current_user, 'is_superuser', False):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Admin permission required")

        # 清理过期粘性文章
        cleaned_count = await article_query_service.clean_expired_sticky_articles(db)

        return ApiResponse(
            success=True,
            data={
                "message": f"Successfully cleaned {cleaned_count} expired sticky articles",
                "cleaned_count": cleaned_count
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in clean_expired_sticky_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
