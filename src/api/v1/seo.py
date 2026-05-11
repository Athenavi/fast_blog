"""
SEO 模块
整合站点地图、robots.txt 等 SEO 相关功能
"""
from fastapi import APIRouter

# 导入站点地图路由
from src.api.v1.sitemap import router as sitemap_router

router = APIRouter(tags=["seo"])

# 包含站点地图路由
router.include_router(sitemap_router)
