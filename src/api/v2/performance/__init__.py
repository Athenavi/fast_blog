"""
性能优化API聚合路由器 - V2统一入口
整合V1的performance相关模块
"""
from fastapi import APIRouter
from src.api.v1.performance.cdn_management import router as cdn_management_router
from src.api.v1.performance.code_splitting_optimization import router as code_splitting_router

# 导入V1的performance子模块
from src.api.v1.performance.cache_management import router as cache_management_router
from src.api.v1.performance.css_optimizer import router as css_optimizer_router
from src.api.v1.performance.http2_config import router as http2_config_router
from src.api.v1.performance.image_lazy_load import router as image_lazy_load_router
from src.api.v1.performance.lazy_load_optimization import router as lazy_load_optimization_router
from src.api.v1.performance.load_balancer import router as load_balancer_router
from src.api.v1.performance.localization import router as localization_router
from src.api.v1.performance.object_cache import router as object_cache_router
from src.api.v1.performance.performance_monitor import router as performance_monitor_router
from src.api.v1.performance.performance_tracking import router as performance_tracking_router
from src.api.v1.performance.query_monitor import router as query_monitor_router
from src.api.v1.performance.query_optimization import router as query_optimization_router
from src.api.v1.performance.resource_optimization import router as resource_optimization_router

# 创建聚合路由器
router = APIRouter(tags=["performance"])

# 按顺序包含子路由
router.include_router(cache_management_router, prefix="/admin/caches")  # /admin/caches/*
router.include_router(cdn_management_router, prefix="/admin/cdn")  # /admin/cdn/*
router.include_router(performance_monitor_router, prefix="/performance-monitor")  # /performance-monitor/*
router.include_router(performance_tracking_router, prefix="/performance-tracking")  # /performance-tracking/*
router.include_router(code_splitting_router, prefix="")  # 代码分割优化
router.include_router(css_optimizer_router, prefix="")  # CSS优化
router.include_router(http2_config_router, prefix="")  # HTTP2配置
router.include_router(image_lazy_load_router, prefix="")  # 图片懒加载
router.include_router(lazy_load_optimization_router, prefix="")  # 懒加载优化
router.include_router(load_balancer_router, prefix="")  # 负载均衡
router.include_router(localization_router, prefix="")  # 本地化
router.include_router(object_cache_router, prefix="")  # 对象缓存
router.include_router(query_monitor_router, prefix="")  # 查询监控
router.include_router(query_optimization_router, prefix="")  # 查询优化
router.include_router(resource_optimization_router, prefix="")  # 资源优化
