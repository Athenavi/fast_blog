"""
V3 SEO 管理 API

权限要求:
  GET    /seo/dashboard        → settings:view
  GET    /seo/keywords         → settings:view
  POST   /seo/suggest          → article:edit
  GET    /seo/orphan-articles  → article:view
"""
import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from src.api.v2._base import ApiResponse
from src.api.v3._deps import get_db
from src.api.v3._permission import Permission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-seo"])


@router.get("/seo/dashboard", summary="SEO 概览")
async def seo_dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    """SEO 数据概览"""
    total = await db.scalar(select(Article.id).where(Article.status == 1))
    return ApiResponse(success=True, data={
        "total_published": total or 0,
    })


@router.get("/seo/keywords", summary="热门关键词")
async def top_keywords(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("settings:view")),
):
    """热门搜索关键词"""
    return ApiResponse(success=True, data={"keywords": []})


@router.post("/seo/suggest", summary="内链建议")
async def internal_link_suggest(
    article_id: int = Body(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("article:edit")),
):
    return ApiResponse(success=True, data={"suggestions": []})


@router.get("/seo/orphan-articles", summary="孤立文章")
async def orphan_articles(
    db: AsyncSession = Depends(get_db),
    _=Depends(Permission("article:view")),
):
    """没有分类的文章"""
    result = await db.execute(
        select(Article).where(Article.category == None)
    )
    articles = result.scalars().all()
    return ApiResponse(success=True, data={
        "orphans": [{"id": a.id, "title": a.title} for a in articles],
    })
