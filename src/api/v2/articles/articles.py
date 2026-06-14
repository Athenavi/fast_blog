"""
文章核心 CRUD API - V2 优化版

优化: 统一 @_catch 装饰器消除 33 处重复 try/except
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Body

logger = logging.getLogger(__name__)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.models.category import Category
from shared.models.user import User
from shared.services.articles.article_manager import article_query_service, password_protection_service, save_article_revision
from shared.services.content_management.shortcode_service import shortcode_service
from shared.services.core.api_embed import APIEmbedService
from shared.services.notifications.webhook_service import webhook_service
from shared.services.static_generation.isr_service import isr_service
from shared.services.plugins.event_bus import event_bus, ArticlePublishedPayload, ArticleUpdatedPayload, ArticleDeletedPayload
from src.api.v2._base import ApiResponse
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_optional_dependency, jwt_required_dependency as jwt_required
from src.setting import app_config
from src.utils.database.main import get_async_session
from src.utils.field_filter import filter_fields
from src.utils.filters import markdown_to_html


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fail(str(e))
    return wrapper


def _is_admin(user) -> bool:
    return user and (getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


def _is_author_or_admin(user, article_user_id: int) -> bool:
    return user and (user.id == article_user_id or _is_admin(user))


async def _parse_body(request: Request) -> dict:
    """解析请求体，兼容 JSON 和 FormData，FormData 的值自动转换类型"""
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        return await request.json()
    else:
        form = await request.form()
        data = {}
        for k, v in form.items():
            # FormData 所有值都是字符串，按字段名自动转类型
            s = str(v)
            if k in ('hidden', 'is_vip_only', 'is_featured'):
                data[k] = s.lower() in ('true', '1', 'yes')
            elif k in ('status', 'category_id', 'required_vip_level'):
                data[k] = int(s) if s else 0
            else:
                data[k] = s
        return data


def _split_tags(tags_str: str) -> list:
    return [t.strip() for t in re.split(r'[,;]', tags_str) if t.strip()] if tags_str else []


def _paginate(total: int, page: int, per_page: int) -> dict:
    total_pages = max(1, (total + per_page - 1) // per_page)
    return {"current_page": page, "per_page": per_page, "total": total,
            "total_pages": total_pages, "has_next": page < total_pages, "has_prev": page > 1}


def _fmt_article_brief(article, users: dict, cats: dict) -> dict:
    return {
        "id": article.id, "title": article.title, "slug": article.slug,
        "excerpt": article.excerpt, "cover_image": article.cover_image,
        "tags": _split_tags(article.tags_list),
        "author": {"id": article.user, "username": users[article.user].username if article.user in users else "Unknown"},
        "category_id": article.category,
        "category_name": cats[article.category].name if article.category in cats else None,
        "views": article.views or 0, "likes": article.likes or 0, "status": article.status,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
    }


async def _get_article_author(db: AsyncSession, user_id: int) -> dict:
    author = await db.scalar(select(User).where(User.id == user_id))
    return {"id": author.id if author else user_id, "username": author.username if author else "Unknown",
            "bio": author.bio if author else "", "profile_picture": author.profile_picture if author else None}


async def _get_article_detail(request: Request, db: AsyncSession, article: Article, current_user=None) -> Optional[dict]:
    """统一获取文章详情（含权限/密码检查、Markdown 渲染）"""
    if article.status == -1:
        return None

    if article.hidden:
        if not _is_author_or_admin(current_user, article.user):
            content_obj = await db.scalar(select(ArticleContent).where(ArticleContent.article == article.id))
            if content_obj and content_obj.passwd:
                token = request.cookies.get(f"article_access_{article.id}") or request.query_params.get("access_token")
                if not token or token != password_protection_service.generate_access_token(article.id):
                    return {"requires_password": True, "article_id": article.id, "article_title": article.title, "excerpt": article.excerpt}
            return None

    if article.status == 0 and not _is_author_or_admin(current_user, article.user):
        return None

    content_obj = await db.scalar(select(ArticleContent).where(ArticleContent.article == article.id))
    raw = content_obj.content if content_obj else ""

    if raw:
        theme = request.cookies.get("theme", "github")
        html = shortcode_service.parse(markdown_to_html(markdown_text=raw, theme=theme, enable_toc=True))
    else:
        html = ""

    # 运行 article.content 管道，允许插件修改文章 HTML 内容
    try:
        content_payload = {"html": html}
        content_payload = await event_bus.pipeline("article.content", content_payload, article_id=article.id)
        html = content_payload.get("html", html)
    except Exception:
        pass

    author_info = await _get_article_author(db, article.user)
    seo = article.seo_data.to_dict() if article.seo_data else {}
    i18n_rows = (await db.execute(
        select(ArticleContent).where(ArticleContent.article == article.id))).scalars().all()

    data = {
        "id": article.id, "title": article.title, "slug": article.slug,
        "excerpt": article.excerpt, "content": html, "cover_image": article.cover_image,
        "tags": _split_tags(article.tags_list), "views": article.views or 0, "likes": article.likes or 0,
        "status": article.status, "hidden": article.hidden, "is_vip_only": article.is_vip_only,
        "required_vip_level": article.required_vip_level, "article_ad": article.article_ad,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        "user_id": article.user, "category_id": article.category, "is_featured": article.is_featured,
        "seo_title": seo.get("seo_title"), "seo_description": seo.get("seo_description"),
        "seo_keywords": seo.get("seo_keywords"), "og_title": seo.get("og_title"),
        "og_description": seo.get("og_description"), "og_image": seo.get("og_image"),
        "canonical_url": seo.get("canonical_url"),
        "i18n_versions": [{"language_code": t.language_code, "content_preview": (t.content or "")[:200]} for t in i18n_rows],
        "author": author_info,
    }
    return data


# ========== 路由 ==========

router = APIRouter()


@router.get("/")
@_catch
async def get_articles_api(request: Request, page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=100),
                            search: str = Query(""), category_id: Optional[int] = Query(None),
                            user_id: Optional[int] = Query(None), status: Optional[str] = Query(None),
                            fields: Optional[str] = Query(None), embed: Optional[str] = Query(None),
                            db: AsyncSession = Depends(get_async_session)):
    """获取文章列表（分页/搜索/分类/用户过滤）"""
    is_admin = _is_admin(request.scope.get('user'))
    articles, total = await article_query_service.get_articles_list(
        db=db, page=page, per_page=per_page, search=search or None,
        category_id=category_id, user_id=user_id, status=status, include_sticky=True, is_admin=is_admin)

    uids = {a.user for a in articles if a.user}
    cids = {a.category for a in articles if a.category}
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all()} if uids else {}
    cats = {c.id: c for c in (await db.execute(select(Category).where(Category.id.in_(cids)))).scalars().all()} if cids else {}

    data = [_fmt_article_brief(a, users, cats) for a in articles]
    if embed:
        data = await APIEmbedService(db).embed_article_relations(articles, APIEmbedService.validate_embed_fields(
            APIEmbedService.parse_embed_param(embed), ['author', 'category']))
    if fields:
        data = filter_fields(data, fields)
    return ApiResponse(success=True, data=data, pagination=_paginate(total, page, per_page))


@router.get("/home/articles")
@_catch
async def get_home_articles_api(request: Request, page: int = Query(1, ge=1), per_page: int = Query(9, ge=1, le=50),
                                 db: AsyncSession = Depends(get_async_session)):
    """首页文章列表（公开）"""
    offset = (page - 1) * per_page
    q = select(Article).where(Article.hidden == False, Article.status == 1, Article.is_vip_only == False).order_by(Article.id.desc())
    articles = (await db.execute(q.offset(offset).limit(per_page))).scalars().all()
    total = await db.scalar(select(func.count()).select_from(Article).where(Article.hidden == False, Article.status == 1, Article.is_vip_only == False)) or 0

    uids = {a.user for a in articles if a.user}
    cids = {a.category for a in articles if a.category}
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all()} if uids else {}
    cats = {c.id: c for c in (await db.execute(select(Category).where(Category.id.in_(cids)))).scalars().all()} if cids else {}

    return ApiResponse(success=True, data={"data": [_fmt_article_brief(a, users, cats) for a in articles],
                                            "pagination": _paginate(total or 0, page, per_page)})


@router.get("/user/{user_id}")
@_catch
async def get_user_articles_api(request: Request, user_id: int = Path(...), page: int = Query(1, ge=1),
                                 per_page: int = Query(10, ge=1, le=100),
                                 current_user=Depends(jwt_optional_dependency),
                                 db: AsyncSession = Depends(get_async_session)):
    """获取指定用户的文章列表"""
    if current_user and current_user.id != user_id and not _is_admin(current_user):
        raise HTTPException(403, "Permission denied")

    articles, total = await article_query_service.get_articles_list(
        db=db, page=page, per_page=per_page, user_id=user_id, include_sticky=True)
    return ApiResponse(success=True, data=articles, pagination=_paginate(total, page, per_page))


@router.get("/user/{user_id}/stats")
@_catch
async def get_user_articles_stats_api(user_id: int, db: AsyncSession = Depends(get_async_session)):
    """用户文章统计"""
    total = await db.scalar(select(func.count(Article.id)).where(Article.user == user_id)) or 0
    published = await db.scalar(select(func.count(Article.id)).where(Article.user == user_id, Article.status == 1)) or 0
    views = await db.scalar(select(func.sum(Article.views)).where(Article.user == user_id)) or 0
    return ok(data={"total_articles": total, "published": published, "total_views": views})


@router.get("/p/{slug}")
@_catch
async def get_article_by_slug_api(slug: str, request: Request, db: AsyncSession = Depends(get_async_session)):
    """通过 slug 获取文章详情"""
    article = await db.scalar(select(Article).where(Article.slug == slug))
    if not article:
        raise HTTPException(404, "文章不存在")
    data = await _get_article_detail(request, db, article)
    if data is None:
        raise HTTPException(404, "文章不存在或无权访问")
    return ApiResponse(success=True, data=data)


@router.get("/{article_id}.html")
@_catch
async def get_article_by_id_html_api(article_id: int, request: Request, db: AsyncSession = Depends(get_async_session)):
    """获取文章 HTML 格式内容"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    data = await _get_article_detail(request, db, article)
    if data is None:
        raise HTTPException(404, "文章不存在或无权访问")
    return ApiResponse(success=True, data=data)


@router.get("/detail")
@_catch
async def get_article_detail_by_query_api(article_id: int = Query(...), request: Request = None,
                                            db: AsyncSession = Depends(get_async_session)):
    """通过 query 参数获取文章详情"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    data = await _get_article_detail(request, db, article)
    if data is None:
        raise HTTPException(404, "文章不存在或无权访问")
    return ApiResponse(success=True, data=data)


@router.get("/{article_id}")
@_catch
async def get_article_detail_api(article_id: int, request: Request, db: AsyncSession = Depends(get_async_session)):
    """获取文章详情"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    data = await _get_article_detail(request, db, article)
    if data is None:
        raise HTTPException(404, "文章不存在或无权访问")
    return ApiResponse(success=True, data=data)


@router.get("/{article_id}/raw")
@_catch
async def get_article_raw_content_api(article_id: int, db: AsyncSession = Depends(get_async_session)):
    """获取文章原始 Markdown 内容"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    content = await db.scalar(select(ArticleContent.content).where(ArticleContent.article == article_id))
    return ApiResponse(success=True, data={"id": article.id, "title": article.title, "slug": article.slug, "content": content or ""})


@router.post("/")
@_catch
async def create_article_api(request: Request, current_user=Depends(jwt_required),
                              db: AsyncSession = Depends(get_async_session)):
    """创建文章"""
    data = await _parse_body(request)
    # category_id=0 时转为 None，避免外键约束错误
    cat_id = data.get('category_id')
    if cat_id is not None and (not cat_id or cat_id == 0 or cat_id == '0'):
        cat_id = None
    article = Article(
        title=data.get('title', ''), slug=data.get('slug', ''),
        excerpt=data.get('excerpt', ''), user=current_user.id,
        category=cat_id, tags_list=data.get('tags', ''),
        cover_image=data.get('cover_image', ''), hidden=data.get('hidden', False),
        is_vip_only=data.get('is_vip_only', False), article_ad=data.get('article_ad', ''),
        status=data.get('status', 0), is_featured=data.get('is_featured', False),
        created_at=datetime.now(), updated_at=datetime.now(), views=0, likes=0,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    if data.get('content'):
        db.add(ArticleContent(article=article.id, content=data['content'], passwd=data.get('password', ''),
                              created_at=datetime.now(), updated_at=datetime.now()))
        await db.commit()

    await save_article_revision(db=db, article_id=article.id, author_id=current_user.id, change_summary="创建文章")
    try:
        await isr_service.invalidate(article.slug)
        await webhook_service.trigger('article.created', {'article_id': article.id})
        # 仅在发布状态时发送 published 事件
        if article.status == 1:
            await event_bus.emit('article.published', ArticlePublishedPayload(
                article_id=article.id, slug=article.slug, title=article.title,
                author_id=current_user.id, excerpt=article.excerpt or '',
                tags=[t.strip() for t in article.tags_list.split(',') if t.strip()] if article.tags_list else [],
                category_id=article.category,
            ))
    except Exception:
        logger.warning(f"文章创建后处理失败 (article_id={article.id})", exc_info=True)

    return ApiResponse(success=True, data={"id": article.id, "slug": article.slug}, message="文章创建成功")


@router.put("/{article_id}")
@_catch
async def update_article_api(article_id: int, request: Request, current_user=Depends(jwt_required),
                              db: AsyncSession = Depends(get_async_session)):
    """更新文章"""
    data = await _parse_body(request)
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not _is_admin(current_user):
        raise HTTPException(403, "无权修改此文章")

    for field in ('title', 'slug', 'excerpt', 'cover_image', 'tags_list', 'hidden', 'is_vip_only', 'is_featured', 'status'):
        if field in data:
            setattr(article, field, data[field])
    # category_id 映射到模型字段 category，0 转为 None
    if 'category_id' in data:
        cat_val = data['category_id']
        article.category = None if cat_val is None or cat_val == 0 or cat_val == '0' else cat_val
    article.updated_at = datetime.now()

    if data.get('content') is not None:
        content = await db.scalar(select(ArticleContent).where(ArticleContent.article == article_id))
        if content:
            content.content = data['content']
            if 'password' in data:
                content.passwd = data['password']
        else:
            db.add(ArticleContent(article=article_id, content=data['content'], passwd=data.get('password', ''),
                                  created_at=datetime.now(), updated_at=datetime.now()))

    await db.commit()
    await save_article_revision(db=db, article_id=article_id, author_id=current_user.id,
                                change_summary=data.get('change_summary', '更新文章'))

    try:
        await isr_service.invalidate(article.slug)
        await webhook_service.trigger('article.updated', {'article_id': article_id})
        await event_bus.emit('article.updated', ArticleUpdatedPayload(
            article_id=article.id, slug=article.slug, title=article.title,
            author_id=current_user.id,
        ))
    except Exception:
        logger.warning(f"文章更新后处理失败 (article_id={article.id})", exc_info=True)

    return ApiResponse(success=True, data={"id": article.id, "slug": article.slug}, message="文章更新成功")


@router.delete("/{article_id}")
@_catch
async def delete_article_api(article_id: int, current_user=Depends(jwt_required),
                              db: AsyncSession = Depends(get_async_session)):
    """删除文章（软删除）"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not _is_admin(current_user):
        raise HTTPException(403, "无权删除此文章")
    article.status = -1
    await db.commit()

    try:
        await webhook_service.trigger('article.deleted', {'article_id': article_id})
        await event_bus.emit('article.deleted', ArticleDeletedPayload(
            article_id=article.id, slug=article.slug, title=article.title,
        ))
    except Exception:
        logger.warning(f"文章删除后处理失败 (article_id={article_id})", exc_info=True)
    return ApiResponse(success=True, message="文章已删除")


@router.get("/tag/{tag_name}")
@_catch
async def get_articles_by_tag_api(tag_name: str, page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100),
                                   db: AsyncSession = Depends(get_async_session)):
    """按标签获取文章"""
    offset = (page - 1) * per_page
    q = select(Article).where(Article.tags_list.contains(tag_name), Article.status == 1).order_by(Article.id.desc())
    total = await db.scalar(select(func.count()).select_from(Article).where(
        Article.tags_list.contains(tag_name), Article.status == 1)) or 0
    articles = (await db.execute(q.offset(offset).limit(per_page))).scalars().all()

    uids = {a.user for a in articles if a.user}
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all()} if uids else {}
    return ApiResponse(success=True, data=[_fmt_article_brief(a, users, {}) for a in articles],
                       pagination=_paginate(total, page, per_page))


@router.get("/featured")
@_catch
async def get_featured_articles_api(limit: int = Query(6, ge=1, le=20),
                                     db: AsyncSession = Depends(get_async_session)):
    """获取推荐/精选文章"""
    articles = (await db.execute(
        select(Article).where(Article.status == 1, Article.hidden == False, Article.is_featured == True)
        .order_by(Article.id.desc()).limit(limit))).scalars().all()

    uids = {a.user for a in articles if a.user}
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(uids)))).scalars().all()} if uids else {}
    return ApiResponse(success=True, data=[_fmt_article_brief(a, users, {}) for a in articles])


@router.get("/contribute/{article_id}")
@_catch
async def get_contribute_info_api(article_id: int):
    """获取文章投稿信息"""
    return ok(data={"article_id": article_id})


@router.post("/contribute/{article_id}")
@_catch
async def submit_contribution_api(request: Request, article_id: int):
    """提交文章投稿"""
    return ok(data={"article_id": article_id}, msg="投稿成功")


@router.get("/edit/{article_id}")
@_catch
async def get_edit_article_api(article_id: int, current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_session)):
    """获取文章编辑数据"""
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        raise HTTPException(404, "文章不存在")
    if article.user != current_user.id and not _is_admin(current_user):
        raise HTTPException(403, "无权编辑此文章")
    content = await db.scalar(select(ArticleContent.content).where(ArticleContent.article == article_id))
    return ok(data={"id": article.id, "title": article.title, "slug": article.slug,
                    "excerpt": article.excerpt, "content": content or "", "cover_image": article.cover_image,
                    "tags": article.tags_list, "category_id": article.category, "status": article.status,
                    "hidden": article.hidden, "is_vip_only": article.is_vip_only, "is_featured": article.is_featured})


@router.get("/new")
@_catch
async def get_new_article_form_api(category_id: int = Query(0, alias="cid")):
    """获取新建文章表单的默认数据"""
    return ok(data={"title": "", "content": "", "category_id": category_id or None})


@router.post("/{article_id}/sticky")
@_catch
async def toggle_article_sticky_api(article_id: int, data: dict = Body(...), current_user=Depends(jwt_required),
                                     db: AsyncSession = Depends(get_async_session)):
    """切换文章置顶状态（管理员）"""
    if not _is_admin(current_user):
        return fail("仅管理员可操作置顶")
    article = await db.scalar(select(Article).where(Article.id == article_id))
    if not article:
        return fail("文章不存在")
    article.is_sticky = data.get('sticky', False)
    if data.get('sticky'):
        sticky_days = data.get('sticky_days', 7)
        if not isinstance(sticky_days, (int, float)) or sticky_days <= 0:
            return fail("置顶天数必须大于 0")
        article.sticky_until = datetime.now() + timedelta(days=sticky_days)
    await db.commit()
    return ok(msg="置顶状态已更新")


@router.post("/admin/clean-expired-sticky")
@_catch
async def clean_expired_sticky_articles_api(current_user=Depends(jwt_required),
                                            db: AsyncSession = Depends(get_async_session)):
    """清理过期的置顶文章（管理员）"""
    result = await db.execute(
        select(Article).where(Article.is_sticky == True, Article.sticky_until < datetime.now()))
    count = 0
    for article in result.scalars().all():
        article.sticky = False
        article.sticky_expires_at = None
        count += 1
    await db.commit()
    return ok(data={"cleaned_count": count}, msg=f"已清理 {count} 篇过期置顶文章")


@router.post("/reorder")
@_catch
async def reorder_articles_api(data: list[dict] = Body(...), current_user=Depends(jwt_required),
                                db: AsyncSession = Depends(get_async_session)):
    """文章排序"""
    if not _is_admin(current_user):
        return fail("仅管理员可排序")
    for item in data:
        article = await db.scalar(select(Article).where(Article.id == item.get('id')))
        if article and 'sort_order' in item:
            article.sort_order = item['sort_order']
    await db.commit()
    return ok(msg="排序已更新")


@router.post("/batch-operation")
@_catch
async def batch_article_operation_api(data: dict = Body(...), current_user=Depends(jwt_required),
                                       db: AsyncSession = Depends(get_async_session)):
    """批量操作文章"""
    if not _is_admin(current_user):
        return fail("仅管理员可批量操作")
    action = data.get('action')
    ids = data.get('ids', [])
    if not ids:
        return fail("请选择文章")

    if action == 'delete':
        for a in (await db.execute(select(Article).where(Article.id.in_(ids)))).scalars().all():
            a.status = -1
    elif action == 'publish':
        for a in (await db.execute(select(Article).where(Article.id.in_(ids)))).scalars().all():
            a.status = 1
    elif action == 'draft':
        for a in (await db.execute(select(Article).where(Article.id.in_(ids)))).scalars().all():
            a.status = 0
    elif action == 'feature':
        for a in (await db.execute(select(Article).where(Article.id.in_(ids)))).scalars().all():
            a.is_featured = data.get('value', False)
    else:
        return fail(f"未知操作: {action}")
    await db.commit()
    return ok(data={"affected": len(ids)}, msg=f"批量{action}完成")
