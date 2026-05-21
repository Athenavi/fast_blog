"""
无障碍API聚合路由器 - V2统一入口
整合V1的accessibility相关模块
"""
from fastapi import APIRouter

# 导入V1的accessibility子模块
from src.api.v1.accessibility.accessibility_audit import router as accessibility_audit_router
from src.api.v1.accessibility.amp import router as amp_router

# 创建聚合路由器
router = APIRouter(tags=["accessibility"])

# 按顺序包含子路由
router.include_router(accessibility_audit_router, prefix="/audit")  # /accessibility-audit/*
router.include_router(amp_router, prefix="/amp")  # /amp/*
