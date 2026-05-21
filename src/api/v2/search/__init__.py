"""
搜索API聚合路由器 - V2统一入口
整合V1的search相关模块
"""
from fastapi import APIRouter

# 导入V1的search子模块
from src.api.v1.search.fulltext_search import router as fulltext_search_router

# 创建聚合路由器
router = APIRouter(tags=["search"])

# 包含子路由
router.include_router(fulltext_search_router, prefix="")  # 全文搜索
