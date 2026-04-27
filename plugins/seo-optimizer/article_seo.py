"""
文章 SEO 元数据管理 API
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.user.models import User
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["article-seo"])


@router.get("/articles/{article_id}/seo")
async def get_article_seo(
        article_id: int,
        db: AsyncSession = Depends(get_async_db),
):
    """获取文章 SEO 元数据"""
    stmt = select(ArticleSEO).where(ArticleSEO.article_id == article_id)
    result = await db.execute(stmt)
    seo = result.scalar_one_or_none()

    if not seo:
        # 返回默认值
        return {
            "success": True,
            "data": {
                "article_id": article_id,
                "seo_title": None,
                "seo_description": None,
                "seo_keywords": None,
                "og_title": None,
                "og_description": None,
                "og_image": None,
                "canonical_url": None,
                "robots_meta": "index,follow",
                "schema_org_enabled": True,
                "schema_org_type": "BlogPosting",
            }
        }

    return {"success": True, "data": seo.to_dict()}


@router.post("/articles/{article_id}/seo")
async def update_article_seo(
        article_id: int,
        seo_title: Optional[str] = None,
        seo_description: Optional[str] = None,
        seo_keywords: Optional[str] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        og_image: Optional[str] = None,
        canonical_url: Optional[str] = None,
        robots_meta: str = "index,follow",
        schema_org_enabled: bool = True,
        schema_org_type: str = "BlogPosting",
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required),
):
    """更新文章 SEO 元数据"""
    # 查找或创建 SEO 记录
    stmt = select(ArticleSEO).where(ArticleSEO.article_id == article_id)
    result = await db.execute(stmt)
    seo = result.scalar_one_or_none()

    if seo:
        # 更新现有记录
        if seo_title is not None:
            seo.seo_title = seo_title
        if seo_description is not None:
            seo.seo_description = seo_description
        if seo_keywords is not None:
            seo.seo_keywords = seo_keywords
        if og_title is not None:
            seo.og_title = og_title
        if og_description is not None:
            seo.og_description = og_description
        if og_image is not None:
            seo.og_image = og_image
        if canonical_url is not None:
            seo.canonical_url = canonical_url
        if robots_meta is not None:
            seo.robots_meta = robots_meta
        if schema_org_enabled is not None:
            seo.schema_org_enabled = schema_org_enabled
        if schema_org_type is not None:
            seo.schema_org_type = schema_org_type
    else:
        # 创建新记录
        seo = ArticleSEO(
            article_id=article_id,
            seo_title=seo_title,
            seo_description=seo_description,
            seo_keywords=seo_keywords,
            og_title=og_title,
            og_description=og_description,
            og_image=og_image,
            canonical_url=canonical_url,
            robots_meta=robots_meta,
            schema_org_enabled=schema_org_enabled,
            schema_org_type=schema_org_type,
        )
        db.add(seo)

    await db.commit()
    await db.refresh(seo)

    return {
        "success": True,
        "data": seo.to_dict(),
        "message": "SEO 元数据更新成功"
    }


@router.delete("/articles/{article_id}/seo")
async def delete_article_seo(
        article_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required),
):
    """删除文章 SEO 元数据（恢复默认）"""
    stmt = select(ArticleSEO).where(ArticleSEO.article_id == article_id)
    result = await db.execute(stmt)
    seo = result.scalar_one_or_none()

    if not seo:
        return {"success": True, "message": "SEO 元数据不存在"}

    await db.delete(seo)
    await db.commit()

    return {"success": True, "message": "SEO 元数据已删除，将使用默认值"}
