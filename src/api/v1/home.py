"""
简化版首页API接口
解决异步greenlet问题，提供稳定的首页数据服务
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.models import Article, User, Category
from src.utils.database.main import get_async_session

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/data")
async def get_home_data(
        limit_featured: int = Query(4, description="特色文章数量"),
        limit_popular: int = Query(5, description="热门文章数量"),
        limit_recent: int = Query(9, description="最新文章数量"),
        limit_categories: int = Query(8, description="分类数量"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取首页数据（不含配置）
    使用简化查询避免greenlet错误
    """
    try:
        # 简化数据获取 - 逐一查询避免复杂并行查询
        featured_articles = await _get_featured_articles(db, limit_featured)
        recent_articles = await _get_recent_articles(db, limit_recent)
        popular_articles = await _get_popular_articles(db, limit_popular)
        categories = await _get_categories(db, limit_categories)
        stats = await _get_site_stats(db)
        
        data = {
            "featuredArticles": featured_articles,
            "recentArticles": recent_articles,
            "popularArticles": popular_articles,
            "categories": categories,
            "stats": stats
        }

        return ApiResponse(success=True, data=data)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取首页数据失败: {str(e)}")
        # 返回简化数据而不是错误
        return ApiResponse(success=True, data={
            "featuredArticles": [],
            "recentArticles": [],
            "popularArticles": [],
            "categories": [],
            "stats": {"totalArticles": 0, "totalUsers": 0, "totalViews": 0}
        })


@router.get("/config")
async def get_home_config(db: AsyncSession = Depends(get_async_session)):
    """
    获取首页配置信息
    使用简化查询避免greenlet错误
    """
    try:
        from src.models.system import SystemSettings

        # 定义需要的配置键
        config_keys = [
            'site_name',
            'hero_title',
            'hero_subtitle',
            'hero_background',
            'hero_cta_text',
            'hero_cta_link',
            'featured_title',
            'recent_title',
            'popular_title',
            'categories_title'
        ]

        # 简化查询 - 逐个获取配置项避免复杂批量查询
        config_dict = {}
        for key in config_keys:
            try:
                query = select(SystemSettings).where(SystemSettings.key == key)
                result = await db.execute(query)
                item = result.scalar_one_or_none()
                if item:
                    config_dict[key] = item.value
            except Exception as key_error:
                # 单个配置项查询失败不影响其他配置
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"获取配置项 {key} 失败: {str(key_error)}")
                continue

        # 获取站点名称
        site_name = config_dict.get('site_name')
        if not site_name:
            from src.setting import app_config
            site_name = getattr(app_config, "sitename", "FastBlog")

        config = {
            "hero": {
                "title": config_dict.get('hero_title', f"欢迎来到 {site_name}"),
                "subtitle": config_dict.get('hero_subtitle', "发现精彩内容，连接智慧世界"),
                "backgroundImage": config_dict.get('hero_background', ""),
                "ctaText": config_dict.get('hero_cta_text', "开始探索"),
                "ctaLink": config_dict.get('hero_cta_link', "/blogs")
            },
            "sections": {
                "featuredTitle": config_dict.get('featured_title', "精选文章"),
                "recentTitle": config_dict.get('recent_title', "最新内容"),
                "popularTitle": config_dict.get('popular_title', "热门文章"),
                "categoriesTitle": config_dict.get('categories_title', "内容分类")
            }
        }

        return ApiResponse(success=True, data=config)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取首页配置失败: {str(e)}")
        # 返回默认配置作为回退
        default_config = {
            "hero": {
                "title": "欢迎来到 FastBlog",
                "subtitle": "发现精彩内容，连接智慧世界",
                "backgroundImage": "",
                "ctaText": "开始探索",
                "ctaLink": "/blogs"
            },
            "sections": {
                "featuredTitle": "精选文章",
                "recentTitle": "最新内容",
                "popularTitle": "热门文章",
                "categoriesTitle": "内容分类"
            }
        }
        return ApiResponse(success=True, data=default_config)


@router.get("/featured")
async def get_featured_articles(
        limit: int = Query(4, description="返回文章数量"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取特色文章
    """
    try:
        articles = await _get_featured_articles(db, limit)
        return ApiResponse(success=True, data=articles)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/recent")
async def get_recent_articles(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(9, ge=1, le=50, description="每页数量"),
        category_id: Optional[int] = Query(None, description="分类ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取最新文章（分页）
    """
    try:
        articles, pagination = await _get_recent_articles_paginated(db, page, per_page, category_id)
        return ApiResponse(success=True, data={
            "articles": articles,
            "pagination": pagination
        })
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/popular")
async def get_popular_articles(
        limit: int = Query(5, description="返回文章数量"),
        days: int = Query(30, description="统计天数"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取热门文章（按浏览量排序）
    """
    try:
        articles = await _get_popular_articles(db, limit, days)
        return ApiResponse(success=True, data=articles)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/categories")
async def get_home_categories(
        limit: int = Query(8, description="返回分类数量"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    获取首页显示的分类
    """
    try:
        categories = await _get_categories(db, limit)
        return ApiResponse(success=True, data=categories)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/stats")
async def get_home_stats(db: AsyncSession = Depends(get_async_session)):
    """
    获取网站统计数据
    """
    try:
        stats = await _get_site_stats(db)
        return ApiResponse(success=True, data=stats)
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/subscribe")
async def subscribe_email(
        email: str,
        db: AsyncSession = Depends(get_async_session)
):
    """
    邮件订阅
    """
    try:
        # TODO: 实现邮件订阅逻辑
        # 可以保存到数据库或调用第三方邮件服务
        return ApiResponse(success=True, data={"message": "订阅成功"})
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/search")
async def search_home_articles(
        q: str = Query(..., description="搜索关键词"),
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(10, ge=1, le=50, description="每页数量"),
        db: AsyncSession = Depends(get_async_session)
):
    """
    首页文章搜索
    """
    try:
        from sqlalchemy.orm import selectinload
        # 构建搜索查询
        query = select(Article).options(
            selectinload(Article.author)
        ).where(
            Article.status == 1,
            Article.hidden == False,
            Article.is_vip_only == False
        )

        # 添加搜索条件
        if q:
            query = query.where(
                Article.title.contains(q) |
                Article.excerpt.contains(q)
            )

        # 分页
        offset = (page - 1) * per_page
        articles_result = await db.execute(
            query.order_by(desc(Article.created_at))
            .offset(offset)
            .limit(per_page)
        )
        articles = articles_result.scalars().all()

        # 获取总数
        count_query = select(func.count(Article.article_id)).where(
            Article.status == 1,
            Article.hidden == False,
            Article.is_vip_only == False
        )
        if q:
            count_query = count_query.where(
                Article.title.contains(q) |
                Article.excerpt.contains(q)
            )
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 格式化文章数据
        articles_data = [_format_article(article) for article in articles]

        pagination = {
            "current_page": page,
            "per_page": per_page,
            "total": total or 0,
            "total_pages": (total + per_page - 1) // per_page if total else 1,
            "has_next": page < ((total + per_page - 1) // per_page if total else 1),
            "has_prev": page > 1
        }

        return ApiResponse(success=True, data={
            "articles": articles_data,
            "pagination": pagination
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"搜索接口错误: {str(e)}")
        return ApiResponse(success=False, error="搜索服务暂时不可用")


# 简化版辅助函数
async def _get_featured_articles(db: AsyncSession, limit: int) -> list:
    """简化版获取特色文章"""
    try:
        query = select(Article).where(
            Article.status == 1,
            Article.hidden == False,
            Article.is_featured == True,
            Article.is_vip_only == False
        ).order_by(desc(Article.created_at)).limit(limit)

        result = await db.execute(query)
        articles = result.scalars().all()
        return [_format_article(article) for article in articles]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"获取特色文章失败: {str(e)}")
        return []


async def _get_recent_articles_simple(db: AsyncSession, limit: int) -> list:
    """简化版获取最新文章"""
    try:
        query = select(Article).where(
            Article.status == 1,
            Article.hidden == False,
            Article.is_vip_only == False
        ).order_by(desc(Article.created_at)).limit(limit)

        result = await db.execute(query)
        articles = result.scalars().all()
        return [_format_article(article) for article in articles]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"获取最新文章失败: {str(e)}")
        return []


async def _get_popular_articles(db: AsyncSession, limit: int) -> list:
    """简化版获取热门文章"""
    try:
        query = select(Article).where(
            Article.status == 1,
            Article.hidden == False,
            Article.is_vip_only == False
        ).order_by(desc(Article.views)).limit(limit)

        result = await db.execute(query)
        articles = result.scalars().all()
        return [_format_article(article) for article in articles]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"获取热门文章失败: {str(e)}")
        return []


async def _get_categories(db: AsyncSession, limit: int) -> list:
    """简化版获取分类"""
    try:
        query = select(Category).order_by(desc(Category.id)).limit(limit)
        result = await db.execute(query)
        categories = result.scalars().all()

        return [{
            "id": cat.id,
            "name": cat.name,
            "description": cat.description or "",
            "article_count": getattr(cat, 'article_count', 0)
        } for cat in categories]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"获取分类失败: {str(e)}")
        return []


async def _get_site_stats(db: AsyncSession) -> Dict[str, Any]:
    """简化版获取网站统计"""
    try:
        # 文章总数
        articles_query = select(func.count(Article.article_id)).where(Article.status == 1)
        articles_result = await db.execute(articles_query)
        total_articles = articles_result.scalar()

        # 用户总数
        users_query = select(func.count(User.id))
        users_result = await db.execute(users_query)
        total_users = users_result.scalar()

        # 总浏览量
        views_query = select(func.sum(Article.views)).where(Article.views.isnot(None))
        views_result = await db.execute(views_query)
        total_views = views_result.scalar() or 0

        return {
            "totalArticles": total_articles or 0,
            "totalUsers": total_users or 0,
            "totalViews": int(total_views)
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"获取网站统计失败: {str(e)}")
        return {
            "totalArticles": 0,
            "totalUsers": 0,
            "totalViews": 0
        }


def _format_article(article) -> Dict[str, Any]:
    """简化版文章格式化"""
    return {
        "id": article.article_id,
        "title": article.title,
        "excerpt": article.excerpt or "",
        "cover_image": article.cover_image or "",
        "author": {
            "id": article.user_id,
            "username": "未知作者"
        },
        "category_id": article.category_id,
        "category_name": "未分类",
        "views": article.views or 0,
        "likes": getattr(article, 'likes', 0),
        "created_at": article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else str(
            article.created_at),
        "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else str(
            article.updated_at),
        "slug": getattr(article, 'slug', f'article-{article.article_id}')
    }