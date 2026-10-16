"""recommend 模块路由（任务 12：推荐类）

::

    GET /api/v3/content/recommend/related/{article_id}    相关文章（公开）
    GET /api/v3/content/recommend/popular                 热门文章（公开）
    GET /api/v3/content/recommend/trending-tags           热门标签（公开）
    GET /api/v3/content/recommend/for-me                  个性化推荐（登录）
    GET /api/v3/content/recommend/tags/{article_id}       标签建议（需 article:view）

公开读只返回已发布文章的公开字段（标题 / slug / 摘要 / 标签 / 计数），不含正文与草稿。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.recommend.service import recommend_service

router = APIRouter(prefix="/recommend", tags=["content-recommend"], route_class=OperationLogRoute)


@router.get("/related/{article_id}", response_model=ResponseModel, summary="相关文章（公开）")
async def related_articles(
    article_id: int,
    db: DBSession,
    limit: int = Query(default=8, ge=1, le=50),
) -> dict:
    """按「标签 Jaccard 相似度 ×0.7 + 同分类 ×0.2 + 热度 ×0.1」排序，返回分项分数"""
    return resp.success(await recommend_service.related(db, article_id, limit=limit))


@router.get("/popular", response_model=ResponseModel, summary="热门文章（公开）")
async def popular_articles(
    db: DBSession,
    days: Optional[int] = Query(default=None, ge=1, le=365, description="留空=累计 views；指定=窗口内真实浏览量"),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    return resp.success(await recommend_service.popular(db, days=days, limit=limit))


@router.get("/trending-tags", response_model=ResponseModel, summary="热门标签（公开）")
async def trending_tags(
    db: DBSession,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return resp.success(await recommend_service.trending_tags(db, days=days, limit=limit))


@router.get("/for-me", response_model=ResponseModel, summary="个性化推荐（登录）")
async def recommend_for_me(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """兴趣画像来自真实行为：``article_likes``（×3）+ ``page_views``（×1），30 天衰减"""
    return resp.success(await recommend_service.for_user(db, int(current.id), limit=limit))


@router.get("/tags/{article_id}", response_model=ResponseModel, summary="标签建议")
async def tag_suggestions(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
    limit: int = Query(default=10, ge=1, le=30),
) -> dict:
    """正文关键词（复用技能框架的 n-gram 算法）+ 标注是否已在标签库 / 已在本文"""
    return resp.success(await recommend_service.tag_suggestions(db, article_id, limit=limit))
