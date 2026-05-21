"""
聊天API聚合路由器 - V2统一入口
整合V1的chat相关模块
"""
from fastapi import APIRouter

# 导入V1的chat子模块
from src.api.v1.chat.chat import router as chat_router
from src.api.v1.chat.chat_groups import router as chat_groups_router
from src.api.v1.chat.private_messages import router as private_messages_router

# 创建聚合路由器
router = APIRouter(tags=["chat"])

# 按顺序包含子路由
# 注意：具体路径的路由必须先于通配符路由注册，避免路径冲突
router.include_router(chat_groups_router, prefix="/groups")  # /groups/* - 群聊管理
router.include_router(private_messages_router, prefix="/messages/private")  # /messages/private/* - 私聊
router.include_router(chat_router, prefix="")  # 通用聊天路由（必须最后）
