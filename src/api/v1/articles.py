"""
文章相关API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.models import Article, ArticleContent, User
from src.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.filters import md2html

router = APIRouter()


@router.get("/articles",
            summary="获取文章列表",
            description="获取分页的文章列表，支持搜索、分类筛选和用户筛选功能",
            response_description="返回文章列表和分页信息")
async def get_articles_api(
        page: int = Query(1, ge=1, description="页码，从1开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100之间"),
        search: str = Query("", description="搜索关键词，用于标题和摘要搜索"),
        category_id: Optional[int] = Query(None, description="分类ID，用于筛选特定分类的文章"),
        user_id: Optional[int] = Query(None, description="用户ID，用于筛选特定用户的文章"),
        status: Optional[str] = Query(None, description="状态筛选，可选值: draft, published, deleted"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取文章列表API
    """
    try:
        # 构建查询
        from sqlalchemy.orm import selectinload
        query = select(Article).options(selectinload(Article.author)).join(User, Article.user_id == User.id)

        # 搜索功能
        if search:
            query = query.where(
                Article.title.contains(search) |
                Article.excerpt.contains(search)
            )

        # 分类筛选
        if category_id:
            query = query.where(Article.category_id == category_id)

        # 用户筛选
        if user_id:
            query = query.where(Article.user_id == user_id)

        # 状态筛选
        if status:
            if status == 'draft':
                query = query.where(Article.status == 0)  # 草稿对应状态0
            elif status == 'published':
                query = query.where(Article.status == 1)  # 已发布对应状态1
            elif status == 'deleted':
                query = query.where(Article.status == -1)  # 已删除对应状态-1

        # 分页
        offset = (page - 1) * per_page

        # 获取文章
        articles_result = await db.execute(query.offset(offset).limit(per_page))
        articles = articles_result.scalars().all()

        # 获取总数
        total_result = await db.execute(query)
        total = len(total_result.scalars().all())

        # 构建响应数据
        articles_data = []
        for article in articles:
            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "excerpt": article.excerpt,
                "content": getattr(article, 'content', None),  # 如果有内容的话
                "author": {
                    "id": article.user_id,
                    "username": getattr(article.author, 'username', "Unknown") if hasattr(article,
                                                                                          'author') else "Unknown"
                },
                "category_id": article.category_id,
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
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
        print(f"Error in get_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/articles/{article_id}",
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
        from src.models.user import User
        # 正确加载文章及其作者信息
        article_query = select(Article).where(
            Article.article_id == article_id,
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
        article_content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
        article_content_result = await db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        content = article_content.content if article_content else ""

        # 将Markdown内容转换为HTML
        if content:
            content = md2html(content)

        # 单独获取作者信息
        author_query = select(User).where(User.id == article.user_id)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 构建作者信息，确保不为None
        author_info = {
            "id": article.user_id,
            "username": getattr(author, 'username', "Unknown") if author else "Unknown",
            "bio": getattr(author, 'bio', "") if author else "",
            "profile_picture": getattr(author, 'profile_picture', None) if author else None
        }

        article_data = {
            "id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": content,
            "author": author_info,
            "category_id": article.category_id,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                article.updated_at)
        }

        return ApiResponse(success=True, data=article_data)
    except Exception as e:
        import traceback
        print(f"Error in get_article_detail_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/articles/{article_id}/raw",
            summary="获取文章原始内容",
            description="获取文章的原始Markdown格式内容，用于编辑页面",
            response_description="返回文章原始内容，不进行HTML渲染")
async def get_article_raw_content_api(
        request: Request,
        article_id: int,
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取文章原始内容API（不进行HTML渲染）
    专门用于编辑页面，返回原始Markdown格式内容
    """
    try:
        from src.models.user import User
        # 加载文章及其作者信息
        article_query = select(Article).where(
            Article.article_id == article_id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 获取文章原始内容（不进行渲染）
        article_content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
        article_content_result = await db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        raw_content = article_content.content if article_content else ""

        # 获取作者信息
        author_query = select(User).where(User.id == article.user_id)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 构建作者信息
        author_info = {
            "id": article.user_id,
            "username": getattr(author, 'username', "Unknown") if author else "Unknown",
            "bio": getattr(author, 'bio', "") if author else "",
            "profile_picture": getattr(author, 'profile_picture', None) if author else None
        }

        article_data = {
            "id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": raw_content,  # 返回原始内容，不进行渲染
            "author": author_info,
            "category_id": article.category_id,
            "cover_image": article.cover_image,
            "tags": article.tags,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "hidden": article.hidden,
            "is_vip_only": article.is_vip_only,
            "required_vip_level": article.required_vip_level,
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                article.updated_at)
        }

        return ApiResponse(success=True, data=article_data)
    except Exception as e:
        import traceback
        print(f"Error in get_article_raw_content_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/articles",
             summary="创建文章",
             description="创建新文章，需要用户认证",
             response_description="返回创建的文章ID和消息")
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

        new_article = Article(
            title=form_data.get('title', ''),
            slug=slug,
            user_id=current_user.id,  # 当前用户为作者
            excerpt=form_data.get('excerpt', ''),
            cover_image=form_data.get('cover_image', ''),
            tags=form_data.get('tags', ''),
            status=int(form_data.get('status', 0)) if form_data.get('status', '0').isdigit() else 0,
            hidden=form_data.get('hidden') is not None,
            is_vip_only=form_data.get('is_vip_only') is not None,
            required_vip_level=int(form_data.get('required_vip_level', 0)) if form_data.get('required_vip_level',
                                                                                            '0').isdigit() else 0,
            is_featured=form_data.get('is_featured') is not None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 处理分类
        try:
            category_id = form_data.get('category_id')
            if category_id and category_id != 'None' and category_id != '':
                new_article.category_id = int(category_id)
        except ValueError:
            pass  # 如果分类ID无效，保持为None

        db.add(new_article)
        await db.flush()  # 获取新文章的ID

        # 创建文章内容
        content_text = form_data.get('content', '')
        new_content = ArticleContent(
            aid=new_article.article_id,
            content=content_text,
            updated_at=datetime.now()
        )
        db.add(new_content)

        try:
            await db.commit()
            return ApiResponse(
                success=True,
                data={
                    "message": "Article created successfully",
                    "article_id": new_article.article_id
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


@router.put("/articles/{article_id}",
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
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")
        current_user_query = select(UserModel).where(UserModel.id == current_user.id)
        current_user_result = await db.execute(current_user_query)
        current_user_db = current_user_result.scalar_one_or_none()

        # 检查是否是文章作者或者是否具有管理员权限
        is_author = article.user_id == current_user.id
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
                        Article.article_id != article_id  # 排除当前文章本身
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
        article.tags = form_data.get('tags', '')

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
                article.category_id = int(category_id)
            else:
                article.category_id = None
        except ValueError:
            article.category_id = None

        # 更新更新时间
        from datetime import datetime
        article.updated_at = datetime.now()

        # 获取文章内容
        content_text = form_data.get('content', '')

        # 更新或创建文章内容
        from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
        content_result = await db.execute(content_query)
        content = content_result.scalar_one_or_none()
        if content:
            content.content = content_text
            content.updated_at = datetime.now()
        else:
            new_content = ArticleContent(
                aid=article_id,
                content=content_text,
                updated_at=datetime.now()
            )
            db.add(new_content)

        try:
            await db.commit()
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


@router.delete("/articles/{article_id}",
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
    删除文章API
    """
    try:
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            return ApiResponse(success=False, error="Article not found")

        # 检查权限
        if article.user_id != current_user.id:
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


@router.get("/articles/user/{user_id}",
            summary="获取用户文章列表",
            description="获取指定用户的文章列表，需要认证",
            response_description="返回用户文章列表和分页信息")
async def get_user_articles_api(
        request: Request,
        user_id: int,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100之间"),
        current_user: User = Depends(jwt_required),  # 需要认证才能访问
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取指定用户的文章列表API
    """
    try:
        # 检查权限：只能访问自己的文章，或者管理员可以访问任何人的文章
        if current_user.id != user_id and not getattr(current_user, 'is_superuser', False):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")

        # 构建查询 - 只查询指定用户的文章
        from sqlalchemy.orm import selectinload
        query = select(Article).options(selectinload(Article.author)).join(User, Article.user_id == User.id).where(
            Article.user_id == user_id)

        # 分页
        offset = (page - 1) * per_page
        articles_result = await db.execute(query.order_by(Article.created_at.desc()).offset(offset).limit(per_page))
        articles = articles_result.scalars().all()

        total_query = select(func.count()).select_from(Article).where(Article.user_id == user_id)
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 构建响应数据
        articles_data = []
        for article in articles:
            # 获取分类信息
            category_name = None
            if article.category_id:
                from src.models.category import Category
                category_query = select(Category).where(Category.id == article.category_id)
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            # 获取标签信息
            tags_list = []
            if article.tags:
                tags_list = article.tags.split(';')

            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "excerpt": article.excerpt,
                "content": getattr(article, 'content', None),
                "author": {
                    "id": article.user_id,
                    "username": getattr(article.author, 'username', "Unknown") if hasattr(article,
                                                                                          'author') else "Unknown"
                },
                "category_id": article.category_id,
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


@router.get("/articles/user/{user_id}/stats",
            summary="获取用户统计信息",
            description="获取指定用户的统计信息，包括文章数量、关注者等",
            response_description="返回用户统计信息")
async def get_user_articles_stats_api(
        request: Request,
        user_id: int,
        current_user: User = Depends(jwt_required),  # 需要认证才能访问
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取指定用户的统计信息API
    """
    try:
        # 检查权限：只能访问自己的统计信息，或者管理员可以访问任何人的统计信息
        if current_user.id != user_id and not getattr(current_user, 'is_superuser', False):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")

        # 统计文章数量
        articles_count_query = select(func.count()).select_from(Article).where(Article.user_id == user_id)
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
            description="获取适合在首页展示的文章列表，只返回公开的、非VIP的、已发布的文章",
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
        # 构建查询 - 只获取公开的、非VIP的、已发布的文章，并预加载作者信息
        from sqlalchemy.orm import selectinload
        query = select(Article).options(selectinload(Article.author)).join(User, Article.user_id == User.id).where(
            Article.hidden == False,
            Article.status == 1,
            Article.is_vip_only == False
        ).order_by(Article.article_id.desc())

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
            if article.category_id:
                from src.models.category import Category
                category_query = select(Category).where(Category.id == article.category_id)
                category_result = await db.execute(category_query)
                category = category_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            # 处理标签
            tags_list = []
            if article.tags:
                tags_list = article.tags.split(';')

            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "excerpt": article.excerpt,
                "author": {
                    "id": article.user_id,
                    "username": getattr(article.author, 'username', "Unknown") if hasattr(article,
                                                                                          'author') else "Unknown"
                },
                "category_id": article.category_id,
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
