"""
通知API聚合路由器 - V2统一入口
整合V1的notifications相关模块
"""
from fastapi import APIRouter

from src.api.v1.notifications.email_service import router as email_service_router
# 导入V1的notifications子模块
from src.api.v1.notifications.notifications import router as notifications_router
from src.api.v1.notifications.push_notifications import router as push_notifications_router

# 创建聚合路由器
router = APIRouter(tags=["notifications"])

# 按顺序包含子路由
router.include_router(notifications_router, prefix="/for")  # /notifications/* - 主要通知功能
router.include_router(email_service_router, prefix="/email")  # /email/* - 邮件服务
router.include_router(push_notifications_router, prefix="/push")  # /push/* - 推送通知
