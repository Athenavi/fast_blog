"""
静态生成API聚合路由器 - V2统一入口
整合V1的static_generation相关模块
"""
from fastapi import APIRouter

from src.api.v1.static_generation.static_site_generation import router as static_site_generation_router

# 创建聚合路由器
router = APIRouter(tags=["static-generation"])

# 按顺序包含子路由
router.include_router(static_site_generation_router, prefix="/ssg")  # /ssg/* - 静态站点生成
