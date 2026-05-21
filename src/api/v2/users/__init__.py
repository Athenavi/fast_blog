"""
用户模块 - V2 统一入口
整合所有用户相关功能：资料管理、设置、关注、屏蔽等

采用包级别聚合模式，所有子模块通过此文件统一注册
"""
from fastapi import APIRouter

# 导入统一的用户路由器（从 V1 迁移）
from src.api.v1.users.unified_users import router as unified_users_router

router = APIRouter(tags=["users-v2"])

# 包含统一的用户路由
router.include_router(unified_users_router)
