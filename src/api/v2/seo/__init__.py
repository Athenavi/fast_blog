"""
SEO 模块 - V2 统一入口
整合所有 SEO 相关功能：站点地图、robots.txt、面包屑、hreflang、内部链接、重定向管理等

采用包级别聚合模式，所有子模块通过此文件统一注册
"""
from fastapi import APIRouter

# 导入所有 SEO 子模块路由（从 V1 迁移）
from src.api.v1.seo.batch_seo import router as batch_seo_router
from src.api.v1.seo.breadcrumbs import router as breadcrumbs_router
from src.api.v1.seo.content_quality import router as content_quality_router
from src.api.v1.seo.hreflang_api import router as hreflang_router
from src.api.v1.seo.internal_links import router as internal_links_router
from src.api.v1.seo.redirect_management import router as redirect_router
from src.api.v1.seo.schema_generator import router as schema_generator_router
from src.api.v1.seo.seo_dashboard import router as seo_dashboard_router
from src.api.v1.seo.seo_management import router as seo_management_router
from src.api.v1.seo.seo_optimization import router as seo_optimization_router
from src.api.v1.seo.seo_tracking import router as seo_tracking_router
from src.api.v1.seo.sitemap import router as sitemap_router

router = APIRouter(tags=["seo"])

# 包含所有 SEO 子路由
# 注意：子路由的前缀将在 v2 注册时通过主路由前缀 /api/v2/seo 统一管理
router.include_router(sitemap_router, prefix="/sitemap")  # /sitemap/* - 站点地图
router.include_router(breadcrumbs_router, prefix="/breadcrumbs")  # /breadcrumbs/* - 面包屑
router.include_router(hreflang_router, prefix="/hreflang")  # /hreflang/* - hreflang标签
router.include_router(internal_links_router, prefix="/internal-links")  # /internal-links/* - 内部链接
router.include_router(redirect_router, prefix="/redirects")  # /redirects/* - 重定向管理
router.include_router(seo_management_router, prefix="/management")  # /management/* - SEO管理
router.include_router(seo_optimization_router, prefix="/opt")  # /optimization/* - SEO优化
router.include_router(seo_tracking_router, prefix="/tracking")  # /tracking/* - SEO追踪
router.include_router(batch_seo_router, prefix="/batch")  # /batch/* - 批量SEO
router.include_router(content_quality_router, prefix="/content-quality")  # /content-quality/* - 内容质量
router.include_router(schema_generator_router, prefix="/schema")  # /schema/* - Schema生成
router.include_router(seo_dashboard_router, prefix="/dashboard")  # /dashboard/* - SEO仪表板
