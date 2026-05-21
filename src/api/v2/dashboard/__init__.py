"""
仪表板API聚合路由器 - V2统一入口
整合V1的dashboard相关模块
"""
from fastapi import APIRouter

from src.api.v1.dashboard.analytics import router as analytics_router
# 导入V1的dashboard子模块
from src.api.v1.dashboard.dashboard import router as dashboard_router
from src.api.v1.dashboard.realtime_monitor import router as realtime_monitor_router

# 创建聚合路由器
router = APIRouter(tags=["dashboard"])

# 按顺序包含子路由
router.include_router(dashboard_router, prefix="/for")  # /dashboard/* - 主要仪表板功能
router.include_router(analytics_router, prefix="/analytics")  # /analytics/* - 分析
router.include_router(realtime_monitor_router, prefix="/monitor")  # /monitor/* - 实时监控
