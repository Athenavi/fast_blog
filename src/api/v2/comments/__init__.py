"""
评论API聚合路由器 - V2统一入口
整合V1的comments相关模块
"""
from fastapi import APIRouter

from src.api.v1.comments.comment_config import router as comment_config_router
from src.api.v1.comments.comment_subscriptions import router as comment_subscriptions_router
# 导入V1的comments子模块
from src.api.v1.comments.comments import router as comments_router
from src.api.v1.comments.comments_enhanced import router as comments_enhanced_router

# 创建聚合路由器
router = APIRouter(tags=["comments"])

# 按顺序包含子路由
router.include_router(comments_router, prefix="/comments")  # /comments/* - 主要评论功能
router.include_router(comments_enhanced_router, prefix="/comment-plus")  # /comment-plus/* - 增强评论
router.include_router(comment_config_router, prefix="")  # 评论配置
router.include_router(comment_subscriptions_router, prefix="")  # 评论订阅
