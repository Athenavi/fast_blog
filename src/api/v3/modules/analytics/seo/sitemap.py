"""XML 站点地图路由（自 v2 ``src/api/v2/seo/sitemap.py`` 平移，T5-12）

与 v2 的差异：

- 挂载点：``/api/v3/analytics/seo/sitemap/*``（v2 是 ``/api/v2/seo/sitemap/*``），
  ``/sitemap.xml`` 等根路径由 ``src/app.py`` 的 301 重定向指过来；
- **URL 形状改为 Nuxt 实际路由**：文章 ``/articles/{slug}``（无 slug 用
  ``/articles/id/{id}``）、分类 ``/category/{id}``、标签 ``/search?tag=``——
  v2 版还在生成 astro 时代的 ``/blog/p/{slug}`` 死链；
- 修复 v2 版 multilingual 的缩进缺陷（i18n 查询只会在无 slug 分支里执行）；
- 图片/视频 sitemap 的 ``<loc>`` 直接用媒体文件 URL（Nuxt 无公开媒体详情页）。

XML 生成仍复用 ``src/utils/sitemap_generator.py``。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import app_config
from shared.models import Article, Category, Media
from src.api.v3.core.logger import get_logger
from src.utils.database.unified_manager import get_db_session
from src.utils.sitemap_generator import SitemapGenerator, SitemapUrl, SitemapIndex

logger = get_logger("seo.sitemap")

router = APIRouter(tags=["seo-sitemap"])

_CACHE_PUBLIC = {'Cache-Control': 'public, max-age=3600'}
_CACHE_H2 = {'Cache-Control': 'public, max-age=7200'}
_CACHE_D1 = {'Cache-Control': 'public, max-age=86400'}


def _site_url(request: Request) -> str:
    return str(request.base_url).rstrip('/')


def _xml(content: str, headers: dict) -> Response:
    return Response(content=content, media_type='application/xml', headers=headers)


@router.get("/sitemap.xml")
async def get_sitemap_index(request: Request) -> Response:
    """站点地图索引：列出全部子站点地图"""
    base = _site_url(request)
    index = SitemapIndex()
    for name in (
            'sitemap-posts', 'sitemap-categories', 'sitemap-tags', 'sitemap-pages',
            'sitemap-authors', 'sitemap-images', 'sitemap-videos', 'sitemap-multilingual',
    ):
        index.add_sitemap(f'{base}/{name}.xml', datetime.now())
    return _xml(index.generate_xml(), _CACHE_PUBLIC)


@router.get("/sitemap-posts.xml")
async def get_posts_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """文章站点地图（已发布，Nuxt 路由形状）"""
    base = _site_url(request)
    articles = (await db.execute(
        select(Article).where(Article.status == 1).order_by(Article.created_at.desc())
    )).scalars().all()

    generator = SitemapGenerator()
    for article in articles:
        loc = (
            f'{base}/articles/{article.slug}' if article.slug
            else f'{base}/articles/id/{article.id}'
        )
        priority = 0.8 if (article.views or 0) > 100 else 0.6
        fresh = article.updated_at and (datetime.now() - article.updated_at).days < 7
        generator.add_url(SitemapUrl(
            loc=loc,
            lastmod=article.updated_at or article.created_at,
            changefreq='daily' if fresh else 'weekly',
            priority=priority,
        ))
    return _xml(generator.generate_xml(), _CACHE_H2)


@router.get("/sitemap-categories.xml")
async def get_categories_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """分类站点地图（列表页 + 各分类，Nuxt 用 id 路由）"""
    base = _site_url(request)
    categories = (await db.execute(
        select(Category).order_by(Category.name)
    )).scalars().all()

    generator = SitemapGenerator()
    generator.add_url(SitemapUrl(
        loc=f'{base}/categories', lastmod=datetime.now(), changefreq='weekly', priority=0.7,
    ))
    for category in categories:
        generator.add_url(SitemapUrl(
            loc=f'{base}/category/{category.id}',
            lastmod=category.updated_at or category.created_at,
            changefreq='weekly',
            priority=0.6,
        ))
    return _xml(generator.generate_xml(), _CACHE_H2)


@router.get("/sitemap-tags.xml")
async def get_tags_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """标签站点地图：Nuxt 无独立标签页，统一指向搜索页的 tag 过滤"""
    base = _site_url(request)
    articles = (await db.execute(
        select(Article)
        .where(Article.status == 1)
        .where(Article.tags_list.isnot(None))
        .where(Article.tags_list != '')
    )).scalars().all()

    unique_tags: set = set()
    for article in articles:
        if article.tags_list:
            unique_tags.update(tag.strip() for tag in article.tags_list if tag.strip())

    generator = SitemapGenerator()
    generator.add_url(SitemapUrl(
        loc=f'{base}/search', lastmod=datetime.now(), changefreq='weekly', priority=0.6,
    ))
    for tag_name in sorted(unique_tags):
        generator.add_url(SitemapUrl(
            loc=f'{base}/search?tag={tag_name}', lastmod=None, changefreq='weekly', priority=0.5,
        ))
    return _xml(generator.generate_xml(), _CACHE_H2)


@router.get("/sitemap-pages.xml")
async def get_pages_sitemap(request: Request) -> Response:
    """静态页面站点地图（Nuxt 实际存在的公开页面）"""
    base = _site_url(request)
    generator = SitemapGenerator()
    generator.add_url(SitemapUrl(
        loc=base, lastmod=datetime.now(), changefreq='daily', priority=1.0,
    ))
    for path, changefreq, priority in (
            ('/about', 'monthly', 0.5),
            ('/search', 'weekly', 0.6),
            ('/categories', 'weekly', 0.7),
            ('/media', 'weekly', 0.6),
    ):
        generator.add_url(SitemapUrl(
            loc=f'{base}{path}', lastmod=datetime.now(), changefreq=changefreq, priority=priority,
        ))
    return _xml(generator.generate_xml(), _CACHE_D1)


@router.get("/sitemap-authors.xml")
async def get_authors_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """作者站点地图：Nuxt 无公开作者主页，仅保留列表页条目"""
    base = _site_url(request)
    generator = SitemapGenerator()
    generator.add_url(SitemapUrl(
        loc=f'{base}/articles', lastmod=datetime.now(), changefreq='weekly', priority=0.7,
    ))
    return _xml(generator.generate_xml(), _CACHE_H2)


@router.get("/sitemap-images.xml")
async def get_images_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """图片站点地图（公开图片，Google Image Sitemap）"""
    base = _site_url(request)
    images = (await db.execute(
        select(Media)
        .where(Media.file_type == 'image')
        .where(Media.is_public.is_(True))
        .order_by(Media.created_at.desc())
    )).scalars().all()

    generator = SitemapGenerator()
    for image in images:
        image_url = image.file_url or ''
        if image_url and not image_url.startswith('http'):
            image_url = f'{base}{image_url}'
        if not image_url:
            continue
        image_data = {'loc': image_url}
        if image.description:
            image_data['caption'] = image.description
        if image.alt_text:
            image_data['title'] = image.alt_text
        generator.add_url(SitemapUrl(
            loc=image_url,
            lastmod=image.updated_at or image.created_at,
            changefreq='monthly',
            priority=0.6,
            images=[image_data],
        ))
    return _xml(generator.generate_xml(), _CACHE_D1)


@router.get("/sitemap-videos.xml")
async def get_videos_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """视频站点地图（公开视频，Google Video Sitemap）"""
    base = _site_url(request)
    videos = (await db.execute(
        select(Media)
        .where(Media.file_type == 'video')
        .where(Media.is_public.is_(True))
        .order_by(Media.created_at.desc())
    )).scalars().all()

    generator = SitemapGenerator()
    for video in videos:
        video_url = video.file_url or ''
        if video_url and not video_url.startswith('http'):
            video_url = f'{base}{video_url}'
        if not video_url:
            continue
        thumbnail_url = video.thumbnail_url or f'{base}/icon.svg'
        if not thumbnail_url.startswith('http'):
            thumbnail_url = f'{base}{thumbnail_url}'
        video_data = {
            'thumbnail_loc': thumbnail_url,
            'title': video.original_filename or video.filename,
            'description': video.description or f'视频文件: {video.filename}',
            'content_loc': video_url,
        }
        if video.duration:
            video_data['duration'] = video.duration
        if video.created_at:
            video_data['publication_date'] = video.created_at.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        if video.tags:
            video_data['tags'] = [tag.strip() for tag in video.tags.split(',') if tag.strip()]
        generator.add_url(SitemapUrl(
            loc=video_url,
            lastmod=video.updated_at or video.created_at,
            changefreq='monthly',
            priority=0.6,
            videos=[video_data],
        ))
    return _xml(generator.generate_xml(), _CACHE_D1)


@router.get("/sitemap-multilingual.xml")
async def get_multilingual_sitemap(request: Request, db: AsyncSession = Depends(get_db_session)) -> Response:
    """多语言站点地图（hreflang）；单语言站仅输出主 URL + x-default"""
    from shared.models import ArticleContent

    base = _site_url(request)
    articles = (await db.execute(
        select(Article).where(Article.status == 1).order_by(Article.created_at.desc())
    )).scalars().all()

    generator = SitemapGenerator()
    for article in articles:
        main_url = (
            f'{base}/articles/{article.slug}' if article.slug
            else f'{base}/articles/id/{article.id}'
        )
        translations = (await db.execute(
            select(ArticleContent).where(ArticleContent.article == article.id)
        )).scalars().all()

        translation_urls: dict = {}
        for trans in translations:
            if trans.slug:
                translation_urls[trans.language_id] = f'{base}/articles/{trans.slug}'

        alternate_links = [
            {'hreflang': lang, 'href': url} for lang, url in translation_urls.items()
        ]
        if translation_urls:
            alternate_links.append({'hreflang': 'x-default', 'href': main_url})

        priority = 0.8 if (article.views or 0) > 100 else 0.6
        fresh = article.updated_at and (datetime.now() - article.updated_at).days < 7
        generator.add_url(SitemapUrl(
            loc=main_url,
            lastmod=article.updated_at or article.created_at,
            changefreq='daily' if fresh else 'weekly',
            priority=priority,
            alternate_links=alternate_links,
        ))
    return _xml(generator.generate_xml(), _CACHE_H2)


@router.get("/robots.txt")
async def get_robots_txt(request: Request) -> Response:
    """robots.txt（Nuxt 路由形态的爬取规则）"""
    base = _site_url(request)
    robots_content = f"""# robots.txt for {getattr(app_config, 'site_title', None) or 'FastBlog'}
# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /system/
Disallow: /content/
Disallow: /analytics/
Disallow: /extension/
Disallow: /ops/
Disallow: /my/
Disallow: /profile
Disallow: /login
Disallow: /register
Disallow: /api/

Sitemap: {base}/sitemap.xml
"""
    return Response(content=robots_content, media_type='text/plain', headers=_CACHE_D1)
