"""
博客相关API - 包含博客详情、标签、推荐等功能
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.models import Article, ArticleContent, Category
from src.models.user import User

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("/p/{slug}")  # 通过slug访问博客详情
async def get_article_by_slug_api(
        request: Request,
        slug: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    通过slug获取博客详情API
    """
    try:
        # 根据slug获取文章
        from sqlalchemy import select
        article_query = select(Article).where(Article.slug == slug)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 检查文章是否被删除（status为-1）
        if article.status == -1:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 检查文章是否为草稿（status为0）
        # 草稿文章只对作者和管理员可见
        if article.status == 0:
            # 尝试获取当前用户，如果用户未登录或不是文章作者或管理员，则不允许访问
            from fastapi import HTTPException
            from starlette.status import HTTP_403_FORBIDDEN

            # 从请求中尝试获取用户信息（如果有的话）
            current_user = getattr(request.state, 'current_user', None)

            # 如果没有登录或不是文章作者或管理员，则禁止访问
            if not current_user or (current_user.id != article.user_id):
                # 检查用户是否为管理员
                from src.models.user import User
                from sqlalchemy import select
                current_user_db = None
                if current_user:
                    current_user_query = select(User).where(User.id == current_user.id)
                    current_user_result = await db.execute(current_user_query)
                    current_user_db = current_user_result.scalar_one_or_none()
                is_admin = current_user_db and hasattr(current_user_db, 'is_admin') and current_user_db.is_admin

                if not is_admin:
                    return ApiResponse(success=False, error="Article not found", data=None)

        # 获取文章内容
        from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.aid == article.article_id)
        content_result = await db.execute(content_query)
        content = content_result.scalar_one_or_none()

        # 获取作者信息
        from sqlalchemy import select
        from src.models.user import User
        author_query = select(User).where(User.id == article.user_id)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 增加文章浏览量
        article.views = (article.views or 0) + 1
        await db.commit()

        # 获取原始内容并转换为HTML
        raw_content = content.content if content else ""
        from src.utils.filters import md2html
        html_content = md2html(raw_content, enable_toc=True)

        article_data = {
            "id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": html_content,
            "cover_image": article.cover_image,
            "tags": article.tags.split(",") if article.tags else [],
            "views": article.views or 0,
            "likes": article.likes or 0,
            "status": article.status,
            "hidden": article.hidden,
            "is_vip_only": article.is_vip_only,
            "required_vip_level": article.required_vip_level,
            "article_ad": article.article_ad,
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                article.updated_at),
            "user_id": article.user_id,
            "category_id": article.category_id,
            "is_featured": article.is_featured
        }

        author_data = {
            "id": author.id,
            "username": author.username,
            "email": author.email
        } if author else None

        return ApiResponse(
            success=True,
            data={
                "article": article_data,
                "author": author_data
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_article_by_slug_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/{article_id}.html")  # 通过ID获取博客详情
async def get_article_by_id_api(
        request: Request,
        article_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """
    通过ID获取博客详情API
    """
    try:
        # 根据ID获取文章
        from sqlalchemy import select
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 检查文章是否被删除（status为-1）
        if article.status == -1:
            return ApiResponse(success=False, error="Article not found", data=None)

        # 检查文章是否为草稿（status为0）
        # 草稿文章只对作者和管理员可见
        if article.status == 0:
            # 尝试获取当前用户，如果用户未登录或不是文章作者或管理员，则不允许访问
            from fastapi import HTTPException
            from starlette.status import HTTP_403_FORBIDDEN

            # 从请求中尝试获取用户信息（如果有的话）
            current_user = getattr(request.state, 'current_user', None)

            # 如果没有登录或不是文章作者或管理员，则禁止访问
            if not current_user or (current_user.id != article.user_id):
                # 检查用户是否为管理员
                from src.models.user import User
                from sqlalchemy import select
                current_user_db = None
                if current_user:
                    current_user_query = select(User).where(User.id == current_user.id)
                    current_user_result = await db.execute(current_user_query)
                    current_user_db = current_user_result.scalar_one_or_none()
                is_admin = current_user_db and hasattr(current_user_db, 'is_admin') and current_user_db.is_admin

                if not is_admin:
                    return ApiResponse(success=False, error="Article not found", data=None)

        # 获取文章内容
        from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.aid == article.article_id)
        content_result = await db.execute(content_query)
        content = content_result.scalar_one_or_none()

        # 获取作者信息
        from sqlalchemy import select
        from src.models.user import User
        author_query = select(User).where(User.id == article.user_id)
        author_result = await db.execute(author_query)
        author = author_result.scalar_one_or_none()

        # 增加文章浏览量
        article.views = (article.views or 0) + 1
        await db.commit()

        # 获取原始内容并转换为HTML
        raw_content = content.content if content else ""
        from src.utils.filters import md2html
        html_content = md2html(raw_content, enable_toc=True)

        article_data = {
            "id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": html_content,
            "cover_image": article.cover_image,
            "tags": article.tags.split(",") if article.tags else [],
            "views": article.views or 0,
            "likes": article.likes or 0,
            "status": article.status,
            "hidden": article.hidden,
            "is_vip_only": article.is_vip_only,
            "required_vip_level": article.required_vip_level,
            "article_ad": article.article_ad,
            "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                article.created_at),
            "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                article.updated_at),
            "user_id": article.user_id,
            "category_id": article.category_id,
            "is_featured": article.is_featured
        }

        author_data = {
            "id": author.id,
            "username": author.username,
            "email": author.email
        } if author else None

        return ApiResponse(
            success=True,
            data={
                "article": article_data,
                "author": author_data,
                "aid": article_id
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_article_by_id_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/tag/{tag_name}")
async def get_articles_by_tag_api(
        request: Request,
        tag_name: str,
        db: AsyncSession = Depends(get_async_db)
):
    """
    根据标签获取文章列表API
    """
    try:
        # 根据标签名获取相关的文章
        from sqlalchemy import select
        articles_query = select(Article).where(
            Article.tags.like(f"%{tag_name}%"),
            Article.status == 1,  # 只返回已发布的文章
            Article.hidden == False,  # 只返回非隐藏文章
            Article.is_vip_only == False  # 只返回非VIP专属文章
        )
        articles_result = await db.execute(articles_query)
        articles = articles_result.scalars().all()

        articles_data = []
        for article in articles:
            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "slug": article.slug,
                "excerpt": article.excerpt,
                "cover_image": article.cover_image,
                "tags": article.tags.split(",") if article.tags else [],
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "hidden": article.hidden,
                "is_vip_only": article.is_vip_only,
                "required_vip_level": article.required_vip_level,
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at),
                "user_id": article.user_id,
                "category_id": article.category_id,
                "is_featured": article.is_featured
            })

        return ApiResponse(
            success=True,
            data={
                "tag_name": tag_name,
                "articles": articles_data
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_articles_by_tag_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/featured")
async def get_featured_articles_api(
        request: Request,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取推荐文章API
    """
    try:
        # 获取推荐文章（这里假设推荐文章是is_featured字段为True的文章）
        from sqlalchemy import select
        featured_articles_query = select(Article).where(
            Article.is_featured == True,
            Article.status == 1,  # 只返回已发布的文章
            Article.hidden == False,  # 只返回非隐藏文章
            Article.is_vip_only == False  # 只返回非VIP专属文章
        )
        featured_articles_result = await db.execute(featured_articles_query)
        featured_articles = featured_articles_result.scalars().all()

        articles_data = []
        for article in featured_articles:
            articles_data.append({
                "id": article.article_id,
                "title": article.title,
                "slug": article.slug,
                "excerpt": article.excerpt,
                "cover_image": article.cover_image,
                "tags": article.tags.split(",") if article.tags else [],
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "hidden": article.hidden,
                "is_vip_only": article.is_vip_only,
                "required_vip_level": article.required_vip_level,
                "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                    article.created_at),
                "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                    article.updated_at),
                "user_id": article.user_id,
                "category_id": article.category_id,
                "is_featured": article.is_featured
            })

        return ApiResponse(
            success=True,
            data={
                "featured_articles": articles_data
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_featured_articles_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/contribute/{article_id}")
async def get_contribute_info_api(
        request: Request,
        article_id: int
):
    """
    获取贡献翻译信息API
    """
    try:
        return ApiResponse(
            success=True,
            data={
                "aid": article_id
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_contribute_info_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/contribute/{article_id}")
async def submit_contribution_api(
        request: Request,
        article_id: int
):
    """
    提交贡献翻译API
    """
    try:
        data = await request.json()

        # 处理表单提交
        contribute_type = data.get('contribute_type')
        contribute_content = data.get('contribute_content')
        contribute_language = data.get('contribute_language')
        contribute_title = data.get('contribute_title')
        contribute_slug = data.get('contribute_slug')

        # 验证必填字段
        if not all([contribute_type, contribute_content, contribute_language,
                    contribute_title, contribute_slug]):
            return ApiResponse(success=False, error='All fields are required', data=None)

        # 临时返回成功响应
        return ApiResponse(
            success=True,
            data={
                'message': 'Translation submitted successfully',
                'i18n_id': 1
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in submit_contribution_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/edit/{article_id}")
async def get_edit_article_api(
        article_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取编辑文章信息API
    """
    try:
        # 获取文章信息
        from sqlalchemy import select
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="文章不存在", data=None)

        # 检查用户权限：必须是文章作者或管理员
        from sqlalchemy import select
        current_user_query = select(User).where(User.id == current_user.id)
        current_user_result = await db.execute(current_user_query)
        current_user_db = current_user_result.scalar_one_or_none()

        # 检查是否是文章作者或者是否具有管理员权限
        is_author = article.user_id == current_user.id
        is_admin = current_user_db and hasattr(current_user_db, 'is_admin') and current_user_db.is_admin

        if not (is_author or is_admin):
            raise HTTPException(status_code=403, detail="您没有权限编辑此文章")

        # 获取文章内容
        # from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.aid == article.article_id)
        content_result = await db.execute(content_query)
        content = content_result.scalar_one_or_none()

        # 获取所有分类
        # from sqlalchemy import select
        categories_query = select(Category)
        categories_result = await db.execute(categories_query)
        categories = categories_result.scalars().all()

        # 获取VIP计划
        from src.models.vip import VIPPlan
        # from sqlalchemy import select
        vip_plans_query = select(VIPPlan)
        vip_plans_result = await db.execute(vip_plans_query)
        vip_plans = vip_plans_result.scalars().all()

        # 获取站点域名
        from src.setting import app_config
        domain = app_config.domain

        return ApiResponse(
            success=True,
            data={
                "article": {
                    "id": article.article_id,
                    "title": article.title,
                    "slug": article.slug,
                    "excerpt": article.excerpt,
                    "cover_image": article.cover_image,
                    "tags": article.tags.split(",") if article.tags else [],
                    "views": article.views or 0,
                    "likes": article.likes or 0,
                    "status": article.status,
                    "hidden": article.hidden,
                    "is_vip_only": article.is_vip_only,
                    "required_vip_level": article.required_vip_level,
                    "article_ad": article.article_ad,
                    "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
                        article.created_at),
                    "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
                        article.updated_at),
                    "user_id": article.user_id,
                    "category_id": article.category_id,
                    "is_featured": article.is_featured
                },
                "content": content.content if content else "",
                "categories": [{
                    "id": category.id,
                    "name": category.name,
                    "description": category.description
                } for category in categories],
                "vip_plans": [{
                    "id": plan.id,
                    "name": plan.name,
                    "level": plan.level,
                    "price": plan.price
                } for plan in vip_plans],
                "domain": domain
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_edit_article_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/new")
async def get_new_article_form_api(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取新建文章表单信息API
    """
    try:
        # 获取所有分类
        from sqlalchemy import select
        categories_query = select(Category)
        categories_result = await db.execute(categories_query)
        categories = categories_result.scalars().all()

        # 获取VIP计划
        from src.models.vip import VIPPlan
        from sqlalchemy import select
        vip_plans_query = select(VIPPlan)
        vip_plans_result = await db.execute(vip_plans_query)
        vip_plans = vip_plans_result.scalars().all()

        # 获取站点域名
        from src.setting import app_config
        domain = app_config.domain

        return ApiResponse(
            success=True,
            data={
                "categories": [{
                    "id": category.id,
                    "name": category.name,
                    "description": category.description
                } for category in categories],
                "vip_plans": [{
                    "id": plan.id,
                    "name": plan.name,
                    "level": plan.level,
                    "price": plan.price
                } for plan in vip_plans],
                "domain": domain
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_new_article_form_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/edit/{article_id}")
async def update_article_api(
        request: Request,
        article_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新文章API
    """
    try:
        # 获取文章信息
        from sqlalchemy import select
        article_query = select(Article).where(Article.article_id == article_id)
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="文章不存在", data=None)

        # 检查用户权限：必须是文章作者或管理员
        from sqlalchemy import select
        current_user_query = select(User).where(User.id == current_user.id)
        current_user_result = await db.execute(current_user_query)
        current_user_db = current_user_result.scalar_one_or_none()

        # 检查是否是文章作者或者是否具有管理员权限
        is_author = article.user_id == current_user.id
        is_admin = current_user_db and hasattr(current_user_db, 'is_admin') and current_user_db.is_admin

        if not (is_author or is_admin):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="您没有权限编辑此文章")

        # 获取表单数据
        form_data = await request.form()

        # 更新文章基本属性
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
        article.is_vip_only = form_data.get('vipRequired') is not None
        try:
            article.required_vip_level = int(form_data.get('vipRequiredLevel', 0))
        except ValueError:
            article.required_vip_level = 0

        # 处理分类
        try:
            category_id = form_data.get('category')
            if category_id and category_id != 'None':
                article.category_id = int(category_id)
            else:
                article.category_id = None
        except ValueError:
            article.category_id = None

        # 处理广告内容
        article.article_ad = form_data.get('article_ad', '')

        # 更新更新时间
        from datetime import datetime, timezone
        article.updated_at = datetime.now()

        # 获取文章内容
        content_text = form_data.get('content', '')

        # 更新或创建文章内容
        from sqlalchemy import select
        content_query = select(ArticleContent).where(ArticleContent.aid == article.article_id)
        content_result = await db.execute(content_query)
        content = content_result.scalar_one_or_none()
        if content:
            content.content = content_text
            content.updated_at = datetime.now()
        else:
            new_content = ArticleContent(
                aid=article.article_id,
                content=content_text,
                updated_at=datetime.now()
            )
            await db.add(new_content)

        try:
            await db.commit()
            return ApiResponse(
                success=True,
                data={"message": "文章保存成功"}
            )
        except Exception as e:
            await db.rollback()
            return ApiResponse(success=False, error=f"保存文章失败: {str(e)}", data=None)
    except Exception as e:
        import traceback
        print(f"Error in update_article_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/new")
async def create_article_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新文章API
    """
    try:
        # 获取表单数据
        form_data = await request.form()

        # 创建新文章
        from datetime import datetime, timezone

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
            is_vip_only=form_data.get('vipRequired') is not None,
            required_vip_level=int(form_data.get('vipRequiredLevel', 0)) if form_data.get('vipRequiredLevel',
                                                                                          '0').isdigit() else 0,
            article_ad=form_data.get('article_ad', ''),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 处理分类
        try:
            category_id = form_data.get('category')
            if category_id and category_id != 'None':
                new_article.category_id = int(category_id)
        except ValueError:
            pass  # 如果分类ID无效，保持为None

        await db.add(new_article)
        await db.flush()  # 获取新文章的ID

        # 创建文章内容
        content_text = form_data.get('content', '')
        new_content = ArticleContent(
            aid=new_article.article_id,
            content=content_text,
            updated_at=datetime.now()
        )
        await db.add(new_content)

        try:
            await db.commit()
            return ApiResponse(
                success=True,
                data={
                    "message": "文章创建成功",
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
