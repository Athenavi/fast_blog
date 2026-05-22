"""
营销API聚合路由器 - V2统一入口
整合V1的marketing相关模块
"""
from fastapi import APIRouter

# 导入V1的marketing子模块
from src.api.v1.marketing.ad_management import router as ad_management_router
from src.api.v1.marketing.advertisement_system import router as advertisement_system_router

# 创建聚合路由器
router = APIRouter(tags=["marketing"])

# 按顺序包含子路由
router.include_router(ad_management_router, prefix="/admin/ad")  # /admin/ad/*
router.include_router(advertisement_system_router, prefix="/ads")  # /ads/*
