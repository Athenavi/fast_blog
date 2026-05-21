"""
用户API聚合路由器 - V2统一入口
整合V1的users相关模块
"""
from fastapi import APIRouter
from src.api.v1.users.user_blocks import router as user_blocks_router
from src.api.v1.users.user_profile import router as user_profile_router
from src.api.v1.users.user_relations import router as user_relations_router
# 导入V1的users子模块
from src.api.v1.users.users import router as users_router

from src.api.v1.users.user_management import router as user_management_router
from src.api.v1.users.user_settings import router as user_settings_router

# 创建聚合路由器
router = APIRouter(tags=["users"])

# 按顺序包含子路由
router.include_router(users_router, prefix="/users")  # /users/* - 主要用户功能
router.include_router(user_blocks_router, prefix="/user-blocks")  # /user-blocks/*
router.include_router(user_management_router, prefix="/admin/user")  # /admin/user/*
router.include_router(user_profile_router, prefix="/users")  # /users/* - 用户资料
router.include_router(user_relations_router, prefix="")  # 用户关系
router.include_router(user_settings_router, prefix="")  # 用户设置
