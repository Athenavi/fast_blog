"""
使用 Django Ninja 实现的博客 API
兼容原有 FastAPI 语法风格
"""
from typing import Optional

from django.http import HttpRequest
from ninja import Router, Query, Schema

from apps.blog.models import Article, ArticleContent
from apps.category.models import Category
from apps.user.models import User
from django_blog.django_ninja_compat import ApiResponse

router = Router()


# ==================== Schema 定义 ====================

class AuthorSchema(Schema):
    """作者信息 Schema"""
    user_id: int
    username: str
    author_order: int
    contribution: Optional[str] = None


class ArticleListSchema(Schema):
    """文章列表响应 Schema"""
    id: int
    title: str
    slug: str
    excerpt: Optional[str]
    cover_image: Optional[str]
    tags: Optional[str]
    author_id: int  # 第一作者 ID
    author_username: str  # 第一作者用户名
    authors_count: int  # 作者总数
    category_id: Optional[int]
    category_name: Optional[str]
    views: int
    likes: int
    status: int
    created_at: Optional[str]
    updated_at: Optional[str]


@router.get("/articles", summary="获取文章列表")
def get_articles(
        request: HttpRequest,
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(10, ge=1, le=100, description="每页数量"),
        search: str = Query("", description="搜索关键词"),
        category_id: Optional[int] = Query(None, description="分类 ID"),
        user_id: Optional[int] = Query(None, description="用户 ID"),
        status: Optional[str] = Query(None, description="状态筛选"),
):
    """获取文章列表 API"""
    try:
        # 构建查询
        query = Article.objects.select_related('user', 'category').all()

        # 搜索功能
        if search:
            query = query.filter(title__icontains=search) | query.filter(excerpt__icontains=search)

        # 分类筛选
        if category_id:
            query = query.filter(category_id=category_id)

        # 用户筛选
        if user_id:
            query = query.filter(user_id=user_id)

        # 状态筛选
        if status:
            if status == 'draft':
                query = query.filter(status=0)
            elif status == 'published':
                query = query.filter(status=1)
            elif status == 'deleted':
                query = query.filter(status=-1)

        # 非管理员和非作者只能查看已发布的文章
        # 安全地检查用户认证状态（Django HttpRequest）
        is_authenticated = (
            hasattr(request, 'user') and 
            request.user is not None and
            hasattr(request.user, 'is_authenticated') and 
            request.user.is_authenticated
        )
        is_staff = (
            is_authenticated and 
            hasattr(request.user, 'is_staff') and 
            request.user.is_staff
        )
        
        if not is_staff:
            query = query.filter(status=1)

        # 分页
        offset = (page - 1) * per_page
        total = query.count()
        articles = query[offset:offset + per_page]

        # 构建响应数据
        articles_data = []
        for article in articles:
            # 获取作者数量
            authors_count = 1 + ArticleAuthor.objects.filter(article=article).count()

            articles_data.append({
                "id": article.id,
                "title": article.title,
                "slug": article.slug,
                "excerpt": article.excerpt,
                "cover_image": article.cover_image or None,
                "tags": article.tags or None,
                "author_id": article.user_id,  # 第一作者 ID
                "author_username": article.user.username if article.user else "Unknown",
                "authors_count": authors_count,  # 作者总数
                "category_id": article.category_id,
                "category_name": article.category.name if article.category else None,
                "views": article.views or 0,
                "likes": article.likes or 0,
                "status": article.status,
                "created_at": article.created_at.isoformat() if article.created_at else None,
                "updated_at": article.updated_at.isoformat() if article.updated_at else None
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
        print(f"Error in get_articles: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/articles/{article_id}", summary="获取文章详情")
def get_article_detail(request: HttpRequest, article_id: int):
    """获取文章详情 API"""
    try:
        from django.db.models import F

        # 获取文章
        article = Article.objects.select_related('user', 'category').get(
            article_id=article_id,
            status__gte=0  # 排除已删除的文章
        )

        # 增加浏览量
        article.views = (article.views or 0) + 1
        article.save(update_fields=['views'])

        # 获取文章内容
        try:
            content_obj = ArticleContent.objects.get(aid=article_id)
            content = content_obj.content
        except ArticleContent.DoesNotExist:
            content = ""

        # 获取所有作者信息
        authors_data = []
        # 添加第一作者
        authors_data.append({
            "user_id": article.user_id,
            "username": article.user.username if article.user else "Unknown",
            "author_order": 1,
            "contribution": None,
            "is_main_author": True
        })

        # 添加其他作者
        author_rels = ArticleAuthor.objects.filter(article=article).select_related('user').order_by('author_order')
        for author_rel in author_rels:
            authors_data.append({
                "user_id": author_rel.user_id,
                "username": author_rel.user.username,
                "author_order": author_rel.author_order,
                "contribution": author_rel.contribution,
                "is_main_author": False
            })

        # 按作者顺序排序
        authors_data.sort(key=lambda x: x['author_order'])

        # 构建响应数据
        article_data = {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "content": content,
            "cover_image": article.cover_image or None,
            "tags": article.tags or None,
            "authors": authors_data,  # 多作者列表
            "category_id": article.category_id,
            "category_name": article.category.name if article.category else None,
            "views": article.views,
            "likes": article.likes,
            "status": article.status,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "updated_at": article.updated_at.isoformat() if article.updated_at else None
        }

        return ApiResponse(success=True, data=article_data)
    except Article.DoesNotExist:
        return ApiResponse(success=False, error="Article not found", data=None)
    except Exception as e:
        import traceback
        print(f"Error in get_article_detail: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/categories", summary="获取分类列表")
def get_categories(request: HttpRequest):
    """获取分类列表 API"""
    try:
        categories = Category.objects.all()
        categories_data = [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description or "",
                "article_count": c.article_count or 0
            }
            for c in categories
        ]
        return ApiResponse(success=True, data=categories_data)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 文章作者管理 API ====================

@router.get("/articles/{article_id}/authors", summary="获取文章的所有作者")
def get_article_authors(request: HttpRequest, article_id: int):
    """获取文章的所有作者（包括第一作者和其他作者）"""
    try:
        article = Article.objects.get(article_id=article_id)

        authors_data = []
        # 添加第一作者
        authors_data.append({
            "user_id": article.user_id,
            "username": article.user.username if article.user else "Unknown",
            "author_order": 1,
            "contribution": None,
            "is_main_author": True
        })

        # 添加其他作者
        author_rels = ArticleAuthor.objects.filter(article=article).select_related('user').order_by('author_order')
        for author_rel in author_rels:
            authors_data.append({
                "user_id": author_rel.user_id,
                "username": author_rel.user.username,
                "author_order": author_rel.author_order,
                "contribution": author_rel.contribution,
                "is_main_author": False
            })

        # 按作者顺序排序
        authors_data.sort(key=lambda x: x['author_order'])

        return ApiResponse(success=True, data=authors_data)
    except Article.DoesNotExist:
        return ApiResponse(success=False, error="Article not found")
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/articles/{article_id}/authors", summary="添加文章作者")
def add_article_author(
        request: HttpRequest,
        article_id: int,
        user_id: int = Query(..., description="用户 ID"),
        author_order: int = Query(2, ge=2, description="作者顺序（从 2 开始，1 为第一作者）"),
        contribution: str = Query(None, description="贡献描述")
):
    """为文章添加新的作者"""
    try:
        from apps.blog.services import add_author

        article = Article.objects.get(article_id=article_id)
        user = User.objects.get(id=user_id)

        author_rel = add_author(
            article=article,
            user=user,
            author_order=author_order,
            contribution=contribution
        )

        return ApiResponse(
            success=True,
            message="作者添加成功",
            data={
                "user_id": user_id,
                "username": user.username,
                "author_order": author_order,
                "contribution": contribution
            }
        )
    except Article.DoesNotExist:
        return ApiResponse(success=False, error="文章不存在")
    except User.DoesNotExist:
        return ApiResponse(success=False, error="用户不存在")
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/articles/{article_id}/authors/{user_id}", summary="移除文章作者")
def remove_article_author(request: HttpRequest, article_id: int, user_id: int):
    """移除文章的指定作者（不能移除第一作者）"""
    try:
        from apps.blog.services import remove_author

        article = Article.objects.get(article_id=article_id)

        # 不允许移除第一作者
        if article.user_id == user_id:
            return ApiResponse(
                success=False,
                error="不能移除第一作者。如需更改第一作者，请编辑文章基本信息。"
            )

        remove_author(article=article, user_id=user_id)

        return ApiResponse(success=True, message="作者已移除")
    except Article.DoesNotExist:
        return ApiResponse(success=False, error="文章不存在")
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/articles/{article_id}/authors/{user_id}/order", summary="更新作者顺序")
def update_author_order(
        request: HttpRequest,
        article_id: int,
        user_id: int,
        new_order: int = Query(..., ge=1, description="新的作者顺序")
):
    """更新作者在文章中的顺序"""
    try:
        from apps.blog.services import update_author_order

        article = Article.objects.get(article_id=article_id)
        user = User.objects.get(id=user_id)

        # 如果要将作者设置为第一作者，需要特殊处理
        if new_order == 1:
            return ApiResponse(
                success=False,
                error="不能通过此接口将作者设置为第一作者。第一作者由文章的 user_id 字段决定。"
            )

        update_author_order(article=article, user=user, new_order=new_order)

        return ApiResponse(success=True, message="作者顺序已更新")
    except Article.DoesNotExist:
        return ApiResponse(success=False, error="文章不存在")
    except User.DoesNotExist:
        return ApiResponse(success=False, error="用户不存在")
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
