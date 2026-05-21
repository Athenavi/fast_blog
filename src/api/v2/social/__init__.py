"""
社交API聚合路由器 - V2统一入口
整合V1的social相关模块
"""
from fastapi import APIRouter

# 导入V1的social子模块
from src.api.v1.social.share_stats import router as share_stats_router

# 创建聚合路由器
router = APIRouter(tags=["social"])

# 包含子路由
router.include_router(share_stats_router, prefix="")  # 分享统计
