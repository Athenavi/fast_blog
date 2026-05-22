"""
插件API聚合路由器 - V2统一入口
整合V1的plugins相关模块
"""
from fastapi import APIRouter

from src.api.v1.plugins.article_rating import router as article_rating_router
# 导入V1的plugins子模块
from src.api.v1.plugins.plugin_management import router as plugin_management_router

# 创建聚合路由器
router = APIRouter(tags=["plugins"])

# 按顺序包含子路由
router.include_router(plugin_management_router, prefix="")  # 插件管理（根路径）
router.include_router(article_rating_router, prefix="")  # 文章评分
