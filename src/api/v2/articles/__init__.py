"""
文章API聚合路由器 - V2统一入口
整合V1的articles相关模块
"""
from fastapi import APIRouter

from src.api.v1.articles.article_analytics import router as article_analytics_router
from src.api.v1.articles.article_annotations import router as article_annotations_router
# 导入V1的articles子模块
from src.api.v1.articles.article_password import router as article_password_router
from src.api.v1.articles.article_revisions import router as article_revisions_router
from src.api.v1.articles.article_search import router as article_search_router
from src.api.v1.articles.article_stats import router as article_stats_router
from src.api.v1.articles.draft_preview import router as draft_preview_router

from src.api.v1.articles.scheduled_publish import router as scheduled_publish_router

# 创建聚合路由器
router = APIRouter(tags=["articles"])

# 按顺序包含子路由
router.include_router(article_password_router, prefix="")  # - 文章密码
router.include_router(article_revisions_router, prefix="")  # /revisions/* - 文章修订

router.include_router(article_analytics_router, prefix="/analytics")  # /analytics/*
router.include_router(article_annotations_router, prefix="/annotations")  # /article-annotations/*
router.include_router(article_search_router, prefix="/search")  # /search/*
router.include_router(article_stats_router, prefix="/views")  # /views/*
router.include_router(draft_preview_router, prefix="/draft")  # /draft/*
router.include_router(scheduled_publish_router, prefix="/scheduler")  # /scheduler/*
