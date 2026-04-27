"""
XML 站点地图 API
提供标准的 Sitemap 协议支持，包括多语言 hreflang 标签
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.blog.models import Article
from apps.category.models import Category
from shared.models.article_i18n import ArticleI18n
from src.extensions import get_async_db_session as get_async_db
from src.setting import AppConfig
from src.utils.sitemap_generator import SitemapGenerator, SitemapUrl, SitemapIndex

router = APIRouter(tags=["sitemap"])


@router.get("/sitemap.xml")
async def get_sitemap_index(request: Request):
    """
    获取站点地图索引
    
    返回所有站点地图文件的索引，包括多语言版本
    """
    site_url = str(request.base_url).rstrip('/')

    index = SitemapIndex()

    # 添加各个站点地图
    index.add_sitemap(f"{site_url}/sitemap-posts.xml", datetime.now())
    index.add_sitemap(f"{site_url}/sitemap-categories.xml", datetime.now())
    index.add_sitemap(f"{site_url}/sitemap-tags.xml", datetime.now())
    index.add_sitemap(f"{site_url}/sitemap-pages.xml", datetime.now())
    index.add_sitemap(f"{site_url}/sitemap-multilingual.xml", datetime.now())  # 多语言版本

    content = index.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=3600',  # 缓存 1 小时
        }
    )


@router.get("/sitemap-posts.xml")
async def get_posts_sitemap(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取文章站点地图
    
    包含所有已发布的文章
    """

    site_url = str(request.base_url).rstrip('/')

    # 查询所有已发布的文章
    stmt = (
        select(Article)
        .where(Article.status == 1)
        .order_by(Article.created_at.desc())
    )
    result = await db.execute(stmt)
    articles = result.scalars().all()

    generator = SitemapGenerator()

    for article in articles:
        # 构建文章 URL
        if article.slug:
            loc = f"{site_url}/blog/p/{article.slug}"
        else:
            loc = f"{site_url}/blog/{article.id}.html"

        # 根据文章状态设置优先级
        priority = 0.8 if article.views and article.views > 100 else 0.6

        # 设置更新频率
        changefreq = 'daily' if article.updated_at and (datetime.now() - article.updated_at).days < 7 else 'weekly'

        generator.add_url(SitemapUrl(
            loc=loc,
            lastmod=article.updated_at or article.created_at,
            changefreq=changefreq,
            priority=priority,
        ))

    content = generator.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=7200',  # 缓存 2 小时
        }
    )


@router.get("/sitemap-categories.xml")
async def get_categories_sitemap(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取分类站点地图
    """

    site_url = str(request.base_url).rstrip('/')

    # 查询所有分类
    stmt = select(Category).order_by(Category.name)
    result = await db.execute(stmt)
    categories = result.scalars().all()

    generator = SitemapGenerator()

    # 添加分类列表页
    generator.add_url(SitemapUrl(
        loc=f"{site_url}/categories",
        lastmod=datetime.now(),
        changefreq='weekly',
        priority=0.7,
    ))

    # 添加各个分类
    for category in categories:
        generator.add_url(SitemapUrl(
            loc=f"{site_url}/category/{category.slug}",
            lastmod=category.updated_at or category.created_at,
            changefreq='weekly',
            priority=0.6,
        ))

    content = generator.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=7200',
        }
    )


@router.get("/sitemap-tags.xml")
async def get_tags_sitemap(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取标签站点地图
    """

    site_url = str(request.base_url).rstrip('/')

    # 查询所有已发布的文章，提取唯一标签
    stmt = (
        select(Article)
        .where(Article.status == 'published')
        .where(Article.tags_list.isnot(None))
        .where(Article.tags_list != '')
    )
    result = await db.execute(stmt)
    articles = result.scalars().all()

    # 提取所有唯一标签
    unique_tags = set()
    for article in articles:
        if article.tags_list:
            tags = [tag.strip() for tag in article.tags_list.split(',') if tag.strip()]
            unique_tags.update(tags)

    generator = SitemapGenerator()

    # 添加标签列表页
    generator.add_url(SitemapUrl(
        loc=f"{site_url}/tags",
        lastmod=datetime.now(),
        changefreq='weekly',
        priority=0.6,
    ))

    # 添加各个标签
    for tag_name in sorted(unique_tags):
        generator.add_url(SitemapUrl(
            loc=f"{site_url}/tag/{tag_name}",
            lastmod=None,
            changefreq='weekly',
            priority=0.5,
        ))

    content = generator.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=7200',
        }
    )


@router.get("/sitemap-pages.xml")
async def get_pages_sitemap(
        request: Request,
):
    """
    获取静态页面站点地图
    """
    site_url = str(request.base_url).rstrip('/')

    generator = SitemapGenerator()

    # 首页
    generator.add_url(SitemapUrl(
        loc=site_url,
        lastmod=datetime.now(),
        changefreq='daily',
        priority=1.0,
    ))

    # 其他静态页面
    pages = [
        ('/about', 'monthly', 0.5),
        ('/search', 'weekly', 0.6),
        ('/categories', 'weekly', 0.7),
        ('/tags', 'weekly', 0.6),
    ]

    for path, changefreq, priority in pages:
        generator.add_url(SitemapUrl(
            loc=f"{site_url}{path}",
            lastmod=datetime.now(),
            changefreq=changefreq,
            priority=priority,
        ))

    content = generator.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=86400',  # 缓存 24 小时
        }
    )


@router.get("/sitemap-multilingual.xml")
async def get_multilingual_sitemap(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
):
    """
    获取多语言站点地图
    
    包含所有文章的多语言版本和 hreflang 标签
    """
    site_url = str(request.base_url).rstrip('/')

    # 查询所有已发布的文章
    stmt = (
        select(Article)
        .where(Article.status == 'published')
        .order_by(Article.created_at.desc())
    )
    result = await db.execute(stmt)
    articles = result.scalars().all()

    generator = SitemapGenerator()

    for article in articles:
        # 构建主语言URL
        if article.slug:
            main_url = f"{site_url}/blog/p/{article.slug}"
        else:
            main_url = f"{site_url}/blog/{article.id}.html"

        # 查询该文章的所有翻译版本
        i18n_stmt = select(ArticleI18n).where(ArticleI18n.article == article.id)
        i18n_result = await db.execute(i18n_stmt)
        translations = i18n_result.scalars().all()

        # 构建翻译URL映射
        translation_urls = {}
        for trans in translations:
            if trans.slug:
                trans_url = f"{site_url}/{trans.language_id}/blog/p/{trans.slug}"
            else:
                trans_url = f"{site_url}/{trans.language_id}/blog/{article.id}.html"
            translation_urls[trans.language_id] = trans_url

        # 如果有翻译，添加 x-default
        if translation_urls:
            translation_urls['x-default'] = main_url

        # 设置优先级和更新频率
        priority = 0.8 if article.views and article.views > 100 else 0.6
        changefreq = 'daily' if article.updated_at and (datetime.now() - article.updated_at).days < 7 else 'weekly'

        # 构建 alternate links
        alternate_links = []
        for lang, url in translation_urls.items():
            alternate_links.append({
                'hreflang': lang,
                'href': url
            })

        generator.add_url(SitemapUrl(
            loc=main_url,
            lastmod=article.updated_at or article.created_at,
            changefreq=changefreq,
            priority=priority,
            alternate_links=alternate_links
        ))

    content = generator.generate_xml()

    return Response(
        content=content,
        media_type='application/xml',
        headers={
            'Cache-Control': 'public, max-age=7200',
        }
    )


@router.get("/robots.txt")
async def get_robots_txt(request: Request):
    """
    生成 robots.txt 文件
    
    包含站点地图声明和爬虫规则
    """
    site_url = str(request.base_url).rstrip('/')

    robots_content = f"""# robots.txt for {AppConfig.site_title or 'FastBlog'}
# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Allow all crawlers
User-agent: *
Allow: /

# Disallow admin areas
Disallow: /admin/
Disallow: /api/
Disallow: /login
Disallow: /register

# Allow important pages
Allow: /blog/
Allow: /category/
Allow: /tag/

# Sitemap location
Sitemap: {site_url}/sitemap.xml

# Crawl-delay for polite crawling
Crawl-delay: 1
"""

    return Response(
        content=robots_content,
        media_type='text/plain',
        headers={
            'Cache-Control': 'public, max-age=86400',  # 缓存 24 小时
        }
    )
