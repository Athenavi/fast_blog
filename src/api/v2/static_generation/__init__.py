"""
静态生成API聚合路由器 - V2统一入口
整合V1的static_generation相关模块
"""
from fastapi import APIRouter
# 导入V1的static_generation子模块
from src.api.v1.static_generation.page_cache import router as page_cache_router

from src.api.v1.static_generation.static_site_generation import router as static_site_generation_router

# 创建聚合路由器
router = APIRouter(tags=["static-generation"])

# 按顺序包含子路由
router.include_router(page_cache_router, prefix="")  # 页面缓存
router.include_router(static_site_generation_router, prefix="")  # 静态站点生成
