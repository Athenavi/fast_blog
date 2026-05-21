"""
性能监控与优化模块 - V2 统一入口
整合所有性能相关功能：监控、缓存、查询优化、CDN等

采用包级别聚合模式，所有子模块通过此文件统一注册
"""
from fastapi import APIRouter

# ==================== 缓存管理 ====================
from src.api.v1.performance.cache_management import router as cache_management_router
# ==================== 其他优化模块 ====================
from src.api.v1.performance.css_optimizer import router as css_optimizer_router
from src.api.v1.performance.http2_config import router as http2_config_router
from src.api.v1.performance.image_lazy_load import router as image_lazy_load_router
from src.api.v1.performance.lazy_load_optimization import router as lazy_load_optimization_router
from src.api.v1.performance.load_balancer import router as load_balancer_router
from src.api.v1.performance.object_cache import router as object_cache_router
from src.api.v1.performance.page_cache import router as page_cache_router
# ==================== 性能监控 ====================
from src.api.v1.performance.performance_monitor import router as performance_monitor_router
from src.api.v1.performance.query_monitor import router as query_monitor_router
from src.api.v1.performance.query_optimization import router as query_optimization_router
from src.api.v1.performance.resource_optimization import router as resource_optimization_router
from src.api.v1.performance.slow_query_log import router as slow_query_log_router
# ==================== CDN 与优化（V2 版本）====================
from src.api.v2.performance.cdn_optimization import router as cdn_optimization_router

router = APIRouter(tags=["performance-v2"])

# 包含所有性能相关子路由
# 注意：这些子路由的前缀将在 v2 注册时通过主路由前缀统一管理

# 性能监控
router.include_router(performance_monitor_router)
router.include_router(query_monitor_router)
router.include_router(query_optimization_router)
router.include_router(slow_query_log_router)

# 缓存管理
router.include_router(cache_management_router)
router.include_router(object_cache_router)
router.include_router(page_cache_router)

# CDN 与优化
router.include_router(cdn_optimization_router)

# 其他优化模块
router.include_router(css_optimizer_router)
router.include_router(http2_config_router)
router.include_router(image_lazy_load_router)
router.include_router(lazy_load_optimization_router)
router.include_router(load_balancer_router)
router.include_router(resource_optimization_router)
