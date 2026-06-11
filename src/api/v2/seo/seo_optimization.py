"""
SEO优化API端点
"""
from functools import wraps
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from shared.services.seo.seo_service import seo_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["seo"])


# ==================== SEO分析 ====================

@router.post("/analyze")
@_catch
async def analyze_seo(
        request: Request,
        current_user=Depends(jwt_required)
):
    """
    分析文章SEO质量
    """
    body = await request.json()
    article_data = {
        'title': body.get('title', ''),
        'slug': body.get('slug', ''),
        'excerpt': body.get('excerpt', ''),
        'content': body.get('content', ''),
        'cover_image': body.get('cover_image', ''),
        'tags': body.get('tags', [])
    }
    result = seo_service.analyze_article_seo(article_data)
    return ok(data=result)


# ==================== 站点地图 ====================

@router.get("/sitemap.xml")
@_catch
async def get_sitemap():
    """获取XML站点地图(公开访问)"""
    from shared.services.seo.seo_service import SEOService
    from shared.models.article import Article
    from shared.models.category import Category
    from sqlalchemy import select

    db = next(get_async_db())

    stmt = select(Article).where(Article.status == 'published')
    result = await db.execute(stmt)
    articles = result.scalars().all()

    article_list = [
        {
            'id': a.id, 'slug': a.slug, 'title': a.title,
            'excerpt': a.excerpt, 'cover_image': a.cover_image,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'updated_at': a.updated_at.isoformat() if a.updated_at else None,
            'is_featured': a.is_featured
        } for a in articles
    ]

    stmt = select(Category)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    category_list = [
        {'id': c.id, 'slug': c.slug, 'name': c.name}
        for c in categories
    ]

    result = await db.execute(stmt)
    pages = result.scalars().all()

    page_list = [
        {'id': p.id, 'slug': p.slug, 'title': p.title}
        for p in pages
    ]

    seo_svc = SEOService()
    sitemap_xml = seo_svc.generate_sitemap(article_list, category_list, page_list)

    return Response(
        content=sitemap_xml,
        media_type="application/xml"
    )


@router.post("/sitemap/generate")
@_catch
async def generate_sitemap(
        current_user=Depends(jwt_required)
):
    """手动生成站点地图"""
    from shared.services.seo.seo_service import SEOService
    from shared.models.article import Article
    from shared.models.category import Category
    from sqlalchemy import select

    db = next(get_async_db())

    stmt = select(Article).where(Article.status == 'published')
    result = await db.execute(stmt)
    articles = result.scalars().all()

    article_list = [
        {
            'id': a.id, 'slug': a.slug, 'title': a.title,
            'excerpt': a.excerpt, 'cover_image': a.cover_image,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'updated_at': a.updated_at.isoformat() if a.updated_at else None,
            'is_featured': a.is_featured
        } for a in articles
    ]

    stmt = select(Category)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    category_list = [
        {'id': c.id, 'slug': c.slug, 'name': c.name}
        for c in categories
    ]

    seo_svc = SEOService(base_url="https://example.com")
    sitemap_xml = seo_svc.generate_sitemap(articles=article_list, categories=category_list)

    sitemap_path = os.path.join('static', 'sitemap.xml')
    os.makedirs(os.path.dirname(sitemap_path), exist_ok=True)
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)

    return ok(data={"message": "站点地图已生成", "path": sitemap_path})


# ==================== 结构化数据 ====================

@router.get("/schema/article/{article_id}")
@_catch
async def get_article_schema(
        article_id: int,
        current_user=Depends(jwt_required)
):
    """获取文章结构化数据"""
    from shared.services.seo.seo_service import SEOService
    from shared.models.article import Article
    from sqlalchemy import select

    db = next(get_async_db())

    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        return fail("文章不存在")

    article_data = {
        'title': article.title, 'excerpt': article.excerpt,
        'cover_image': article.cover_image,
        'created_at': article.created_at.isoformat() if article.created_at else None,
        'updated_at': article.updated_at.isoformat() if article.updated_at else None,
        'author_name': article.author.nickname if article.author else '',
        'slug': article.slug, 'id': article.id
    }

    seo_svc = SEOService(base_url="https://example.com")
    schema = seo_svc.generate_article_schema(article_data)
    return ok(data={"schema": schema})


@router.get("/schema/breadcrumb")
@_catch
async def get_breadcrumb_schema(
        request: Request,
        current_user=Depends(jwt_required)
):
    """获取面包屑结构化数据"""
    body = await request.json()
    breadcrumbs = body.get('breadcrumbs', [])
    schema = seo_service.generate_breadcrumb_schema(breadcrumbs)
    return ok(data={"schema": schema})


# ==================== 面包屑导航 ====================

@router.get("/breadcrumbs/article/{article_id}")
@_catch
async def get_article_breadcrumbs(
        article_id: int,
        current_user=Depends(jwt_required)
):
    """获取文章面包屑"""
    from shared.services.seo.seo_service import SEOService
    from shared.models.article import Article
    from shared.models.category import Category
    from sqlalchemy import select

    db = next(get_async_db())

    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        return fail("文章不存在")

    category = None
    if article.category_id:
        stmt = select(Category).where(Category.id == article.category_id)
        result = await db.execute(stmt)
        category = result.scalar_one_or_none()

    article_data = {'title': article.title, 'slug': article.slug, 'id': article.id}
    category_data = {'name': category.name, 'slug': category.slug, 'id': category.id} if category else {}

    seo_svc = SEOService(base_url="https://example.com")
    breadcrumbs = seo_svc.generate_breadcrumbs(article=article_data, category=category_data)
    return ok(data={"breadcrumbs": breadcrumbs})


@router.get("/breadcrumbs/category/{category_id}")
@_catch
async def get_category_breadcrumbs(
        category_id: int,
        current_user=Depends(jwt_required)
):
    """获取分类面包屑"""
    from shared.services.seo.seo_service import SEOService
    from shared.models.category import Category
    from sqlalchemy import select

    db = next(get_async_db())

    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        return fail("分类不存在")

    category_data = {'name': category.name, 'slug': category.slug, 'id': category.id}

    seo_svc = SEOService(base_url="https://example.com")
    breadcrumbs = seo_svc.generate_breadcrumbs(category=category_data)
    return ok(data={"breadcrumbs": breadcrumbs})


# ==================== Canonical URL ====================

@router.get("/canonical")
@_catch
async def get_canonical_url(
        path: str = Query(..., description="路径"),
        page: int = Query(None, description="页码"),
        current_user=Depends(jwt_required)
):
    """获取规范URL"""
    canonical_url = seo_service.get_canonical_url(path, page=page)
    canonical_tag = seo_service.generate_canonical_tag(path, page=page)
    return ok(data={"canonical_url": canonical_url, "canonical_tag": canonical_tag})


@router.post("/canonical/normalize")
@_catch
async def normalize_url(
        request: Request,
        current_user=Depends(jwt_required)
):
    """URL规范化 - 统一URL格式"""
    body = await request.json()
    url = body.get('url', '')
    if not url:
        return fail("URL不能为空")
    normalized = seo_service.normalize_url(url)
    return ok(data={"original_url": url, "normalized_url": normalized})


@router.post("/canonical/detect-duplicates")
@_catch
async def detect_duplicate_content(
        request: Request,
        current_user=Depends(jwt_required)
):
    """检测重复内容"""
    body = await request.json()
    urls = body.get('urls', [])
    content_hash = body.get('content_hash')
    if not urls:
        return fail("URL列表不能为空")
    result = seo_service.detect_duplicate_content(urls, content_hash)
    return ok(data=result)


@router.get("/canonical/pagination-tags")
@_catch
async def get_pagination_tags(
        path: str = Query(..., description="基础路径"),
        current_page: int = Query(..., description="当前页码", ge=1),
        total_pages: int = Query(..., description="总页数", ge=1),
        current_user=Depends(jwt_required)
):
    """生成分页相关标签 (rel=prev/next)"""
    tags = seo_service.generate_pagination_tags(path, current_page, total_pages)
    return ok(data={"tags": tags, "current_page": current_page, "total_pages": total_pages})


@router.post("/canonical/select-primary")
@_catch
async def select_primary_url(
        request: Request,
        current_user=Depends(jwt_required)
):
    """主URL选择策略"""
    body = await request.json()
    urls = body.get('urls', [])
    strategy = body.get('strategy', 'shortest')
    if not urls:
        return fail("URL列表不能为空")
    primary_url = seo_service.select_primary_url(urls, strategy)
    return ok(data={"primary_url": primary_url, "strategy": strategy, "total_urls": len(urls)})
