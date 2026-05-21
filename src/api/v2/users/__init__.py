"""
用户API聚合路由器 - V2统一入口
整合V1的users相关模块
"""
from fastapi import APIRouter

from src.api.v1.users.unified_users import router as user_router
from src.api.v1.users.user_management import router as user_management_router
from src.api.v1.users.user_settings import router as user_settings_router

# 创建聚合路由器
router = APIRouter(tags=["users"])

# 按顺序包含子路由
router.include_router(user_router, prefix="/users")
router.include_router(user_management_router, prefix="/admin/for")  # /admin/for/*
router.include_router(user_settings_router, prefix="/settings")  # /settings/* - 用户设置
