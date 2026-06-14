"""
V3 文章管理 API

权限要求:
  GET    /articles              → article:view
  POST   /articles              → article:create
  PUT    /articles/{id}         → article:edit
  DELETE /articles/{id}         → article:delete
  POST   /articles/{id}/publish → article:publish

路由函数内无权限查询 — 全部由 Depends(Permission) 提前完成。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.article import Article, ArticleContent
from shared.models.category import Category
from shared.models.user import User
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db, get_current_user
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-articles"])


# ============================================================
# 列表
# ============================================================

@router.get("/articles", summary="文章列表")
async def list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    status: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("article:view")),
):
    query = select(Article)

    if category_id is not None:
        query = query.where(Article.category == category_id)
    if status is not None:
        query = query.where(Article.status == status)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Article.created_at.desc()).offset(offset).limit(per_page)
    )
    articles = result.scalars().all()

    # 批量加载作者
    user_ids = {a.user for a in articles if a.user}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_result.scalars().all()}
    else:
        users_map = {}

    return ApiResponse(success=True, data={
        "articles": [_article_summary(a, users_map) for a in articles],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    })


# ============================================================
# 详情
# ============================================================

@router.get("/articles/{article_id}", summary="文章详情")
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("article:view")),
):
    result = await db.execute(
        select(Article).options(selectinload(Article.seo_data))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        return ApiResponse(success=False, error="文章不存在")

    content_result = await db.execute(
        select(ArticleContent).where(ArticleContent.article == article_id)
    )
    content = content_result.scalar_one_or_none()

    author = None
    if article.user:
        author_result = await db.execute(select(User).where(User.id == article.user))
        author = author_result.scalar_one_or_none()

    return ApiResponse(success=True, data=_article_detail(article, content, author))


# ============================================================
# 创建
# ============================================================

@router.post("/articles", summary="创建文章", status_code=201)
async def create_article(
    title: str = Body(...),
    content: str = Body(""),
    excerpt: Optional[str] = Body(None),
    slug: Optional[str] = Body(None),
    tags: Optional[str] = Body(None),
    category_id: Optional[int] = Body(None),
    cover_image: Optional[str] = Body(None),
    status: int = Body(0),
    hidden: bool = Body(False),
    is_vip_only: bool = Body(False),
    is_featured: bool = Body(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("article:create")),
):
    now = datetime.now(timezone.utc)
    article = Article(
        title=title,
        excerpt=excerpt,
        slug=slug,
        tags_list=tags,
        user=current_user.id,
        category=category_id,
        cover_image=cover_image,
        status=status,
        hidden=hidden,
        is_vip_only=is_vip_only,
        is_featured=is_featured,
        created_at=now,
        updated_at=now,
    )
    db.add(article)
    await db.flush()
    await db.refresh(article)

    if content:
        article_content = ArticleContent(
            article=article.id,
            content=content,
            created_at=now,
            updated_at=now,
        )
        db.add(article_content)

    await db.commit()
    await db.refresh(article)

    return ApiResponse(success=True, data={"id": article.id, "title": article.title}, message="文章创建成功")


# ============================================================
# 编辑
# ============================================================

@router.put("/articles/{article_id}", summary="编辑文章")
async def update_article(
    article_id: int,
    title: Optional[str] = Body(None),
    content: Optional[str] = Body(None),
    excerpt: Optional[str] = Body(None),
    slug: Optional[str] = Body(None),
    tags: Optional[str] = Body(None),
    category_id: Optional[int] = Body(None),
    cover_image: Optional[str] = Body(None),
    status: Optional[int] = Body(None),
    hidden: Optional[bool] = Body(None),
    is_vip_only: Optional[bool] = Body(None),
    is_featured: Optional[bool] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("article:edit")),
):
    article = await db.get(Article, article_id)
    if not article:
        return ApiResponse(success=False, error="文章不存在")

    # 所有权校验：仅作者或 superuser 可编辑
    if article.user != current_user.id and not current_user.is_superuser:
        return ApiResponse(success=False, error="无权编辑此文章")

    if title is not None:
        article.title = title
    if excerpt is not None:
        article.excerpt = excerpt
    if slug is not None:
        article.slug = slug
    if tags is not None:
        article.tags_list = tags
    if category_id is not None:
        article.category = category_id
    if cover_image is not None:
        article.cover_image = cover_image
    if status is not None:
        article.status = status
    if hidden is not None:
        article.hidden = hidden
    if is_vip_only is not None:
        article.is_vip_only = is_vip_only
    if is_featured is not None:
        article.is_featured = is_featured

    article.updated_at = datetime.now(timezone.utc)

    if content is not None:
        content_result = await db.execute(
            select(ArticleContent).where(ArticleContent.article == article_id)
        )
        article_content = content_result.scalar_one_or_none()
        if article_content:
            article_content.content = content
            article_content.updated_at = datetime.now(timezone.utc)
        else:
            now = datetime.now(timezone.utc)
            db.add(ArticleContent(
                article=article_id,
                content=content,
                created_at=now,
                updated_at=now,
            ))

    await db.commit()

    return ApiResponse(success=True, message="文章更新成功")


# ============================================================
# 删除
# ============================================================

@router.delete("/articles/{article_id}", summary="删除文章（软删除）")
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("article:delete")),
):
    article = await db.get(Article, article_id)
    if not article:
        return ApiResponse(success=False, error="文章不存在")

    # 所有权校验：仅作者或 superuser 可删除
    if article.user != current_user.id and not current_user.is_superuser:
        return ApiResponse(success=False, error="无权删除此文章")

    # 软删除：标记状态而非删除记录
    article.status = -1
    article.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiResponse(success=True, message="文章已删除（软删除）")


# ============================================================
# 发布
# ============================================================

@router.post("/articles/{article_id}/publish", summary="发布文章")
async def publish_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(Permission("article:publish")),
):
    article = await db.get(Article, article_id)
    if not article:
        return ApiResponse(success=False, error="文章不存在")

    # 所有权校验：仅作者或 superuser 可发布
    if article.user != current_user.id and not current_user.is_superuser:
        return ApiResponse(success=False, error="无权发布此文章")

    article.status = 1
    article.published_at = datetime.now(timezone.utc)
    article.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiResponse(success=True, message="文章已发布")


# ============================================================
# 辅助函数
# ============================================================

def _article_summary(a: Article, users_map: dict) -> dict:
    author = users_map.get(a.user)
    return {
        "id": a.id,
        "title": a.title,
        "slug": a.slug,
        "excerpt": a.excerpt[:200] if a.excerpt else "",
        "cover_image": a.cover_image,
        "tags": a.tags_list,
        "status": a.status,
        "hidden": a.hidden,
        "is_featured": a.is_featured,
        "is_vip_only": a.is_vip_only,
        "author": {
            "id": author.id if author else None,
            "username": author.username if author else "Unknown",
        } if author else None,
        "views": a.views or 0,
        "likes": a.likes or 0,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _article_detail(a: Article, content, author) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "slug": a.slug,
        "excerpt": a.excerpt,
        "content": content.content if content else "",
        "cover_image": a.cover_image,
        "tags": a.tags_list,
        "status": a.status,
        "hidden": a.hidden,
        "is_featured": a.is_featured,
        "is_vip_only": a.is_vip_only,
        "author": {
            "id": author.id if author else None,
            "username": author.username if author else "Unknown",
        } if author else None,
        "views": a.views or 0,
        "likes": a.likes or 0,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
