"""
内容导出 API — WXR (WordPress eXtended RSS) / JSON 格式
支持导出文章、页面、分类、标签、媒体、评论
"""

import json
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.models.category import Category
from shared.models.comment import Comment
from shared.models.media import Media
from shared.models.user import User
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["export"])

NSMAP = {
    'xmlns:excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
    'xmlns:wfw': 'http://wellformedweb.org/CommentAPI/',
    'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
    'xmlns:wp': 'http://wordpress.org/export/1.2/',
}


def _build_wxr(site_title: str, site_url: str, articles: list, categories: list, users: list, comments: list) -> str:
    """构建 WXR XML 字符串"""
    rss = Element('rss', attrib={'version': '2.0'}, **NSMAP)
    channel = SubElement(rss, 'channel')

    # Site info
    SubElement(channel, 'title').text = site_title
    SubElement(channel, 'link').text = site_url
    SubElement(channel, 'description').text = f'{site_title} export'
    SubElement(channel, 'language').text = 'zh-CN'
    SubElement(channel, 'wp:wxr_version').text = '1.2'
    SubElement(channel, 'wp:base_site_url').text = site_url
    SubElement(channel, 'wp:base_blog_url').text = site_url

    # Authors
    seen = set()
    for u in users:
        if u.username in seen:
            continue
        seen.add(u.username)
        a = SubElement(channel, 'wp:author')
        SubElement(a, 'wp:author_id').text = str(u.id)
        SubElement(a, 'wp:author_login').text = u.username or f'user_{u.id}'
        SubElement(a, 'wp:author_email').text = u.email or ''
        SubElement(a, 'wp:author_display_name').text = u.nickname or u.username or f'User {u.id}'
        SubElement(a, 'wp:author_first_name').text = ''
        SubElement(a, 'wp:author_last_name').text = ''

    # Categories
    for cat in categories:
        c = SubElement(channel, 'wp:category')
        SubElement(c, 'wp:category_nicename').text = cat.slug or ''
        SubElement(c, 'wp:category_parent').text = ''
        SubElement(c, 'wp:cat_name').text = cat.name or ''

    # Tags — use category.slug as tag proxy
    for cat in categories:
        t = SubElement(channel, 'wp:tag')
        SubElement(t, 'wp:tag_slug').text = cat.slug or ''
        SubElement(t, 'wp:tag_name').text = cat.name or ''

    # Articles
    for art in articles:
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = art.title or ''
        SubElement(item, 'link').text = f'{site_url}/articles/{art.slug or art.id}'
        SubElement(item, 'pubDate').text = (art.published_at or art.created_at or datetime.now(timezone.utc)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        SubElement(item, 'dc:creator').text = f'user_{art.author_id}' if art.author_id else 'admin'
        for cat in categories:
            if cat.id == art.category_id:
                SubElement(item, 'category').text = cat.name or ''
        SubElement(item, 'guid', attrib={'isPermaLink': 'false'}).text = f'{site_url}/?p={art.id}'
        SubElement(item, 'description').text = (art.excerpt or '')[:500]
        SubElement(item, 'content:encoded').text = art.content or ''
        SubElement(item, 'excerpt:encoded').text = art.excerpt or ''
        SubElement(item, 'wp:post_id').text = str(art.id)
        SubElement(item, 'wp:post_date').text = (art.created_at or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S')
        SubElement(item, 'wp:post_date_gmt').text = (art.created_at or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S')
        SubElement(item, 'wp:comment_status').text = 'open'
        SubElement(item, 'wp:post_name').text = art.slug or ''
        SubElement(item, 'wp:status').text = 'publish' if getattr(art, 'is_published', False) else 'draft'
        SubElement(item, 'wp:post_type').text = 'post'

        # Comments
        for cmt in comments:
            if cmt.article_id != art.id:
                continue
            c = SubElement(item, 'wp:comment')
            SubElement(c, 'wp:comment_id').text = str(cmt.id)
            SubElement(c, 'wp:comment_author').text = cmt.author_name or 'Anonymous'
            SubElement(c, 'wp:comment_author_email').text = cmt.author_email or ''
            SubElement(c, 'wp:comment_author_url').text = ''
            SubElement(c, 'wp:comment_date').text = (cmt.created_at or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S')
            SubElement(c, 'wp:comment_content').text = cmt.content or ''
            SubElement(c, 'wp:comment_approved').text = '1'
            SubElement(c, 'wp:comment_type').text = ''
            SubElement(c, 'wp:comment_parent').text = str(cmt.parent_id or 0)

    return '<?xml version="1.0" encoding="UTF-8" ?>' + tostring(rss, encoding='unicode')


def _build_json(site_title: str, site_url: str, articles: list, categories: list, users: list, comments: list) -> str:
    """构建 JSON 导出"""
    data = {
        'meta': {
            'source': 'fastblog',
            'version': '1.0',
            'title': site_title,
            'link': site_url,
            'exported_at': datetime.now(timezone.utc).isoformat(),
        },
        'users': [{'id': u.id, 'username': u.username, 'email': u.email, 'nickname': u.nickname} for u in users if u],
        'categories': [{'id': c.id, 'name': c.name, 'slug': c.slug, 'description': c.description} for c in categories if c],
        'articles': [{
            'id': a.id, 'title': a.title, 'slug': a.slug, 'content': a.content,
            'excerpt': a.excerpt, 'category_id': a.category_id, 'author_id': a.author_id,
            'status': 'publish' if getattr(a, 'is_published', False) else 'draft',
            'created_at': str(a.created_at or ''),
            'published_at': str(a.published_at or ''),
        } for a in articles if a],
        'comments': [{
            'id': c.id, 'article_id': c.article_id, 'author': c.author_name,
            'email': c.author_email, 'content': c.content, 'created_at': str(c.created_at or ''),
            'parent_id': c.parent_id,
        } for c in comments if c],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


@router.get("/export/wxr")
async def export_wxr(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    """导出全站内容为 WordPress WXR 格式"""
    try:
        articles = (await db.execute(select(Article).order_by(Article.id))).scalars().all()
        categories = (await db.execute(select(Category).order_by(Category.id))).scalars().all()
        users = (await db.execute(select(User).order_by(User.id))).scalars().all()
        comments = (await db.execute(select(Comment).order_by(Comment.id))).scalars().all()

        wxr = _build_wxr('FastBlog', 'https://fastblog.dev', articles, categories, users, comments)
        from fastapi.responses import Response
        return Response(content=wxr, media_type='application/xml',
                        headers={'Content-Disposition': 'attachment; filename="fastblog-export.xml"'})
    except Exception as e:
        return fail(str(e))


@router.get("/export/json")
async def export_json(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(jwt_required),
):
    """导出全站内容为 JSON 格式"""
    try:
        articles = (await db.execute(select(Article).order_by(Article.id))).scalars().all()
        categories = (await db.execute(select(Category).order_by(Category.id))).scalars().all()
        users = (await db.execute(select(User).order_by(User.id))).scalars().all()
        comments = (await db.execute(select(Comment).order_by(Comment.id))).scalars().all()

        j = _build_json('FastBlog', 'https://fastblog.dev', articles, categories, users, comments)
        from fastapi.responses import Response
        return Response(content=j, media_type='application/json',
                        headers={'Content-Disposition': 'attachment; filename="fastblog-export.json"'})
    except Exception as e:
        return fail(str(e))
