"""
协作API聚合路由器 - V2统一入口
整合V1的collaboration相关模块
"""
from fastapi import APIRouter

# 导入V1的collaboration子模块
from src.api.v1.collaboration.collaboration_invites import router as collaboration_invites_router
from src.api.v1.collaboration.collaboration_save import router as collaboration_save_router
from src.api.v1.collaboration.team_collaboration import router as team_collaboration_router
from src.api.v1.collaboration.team_comments import router as team_comments_router
from src.api.v1.collaboration.yjs_collaboration import router as yjs_collaboration_router

# 创建聚合路由器
router = APIRouter(tags=["collaboration"])

# 按顺序包含子路由
router.include_router(collaboration_invites_router, prefix="/invites")  # /collaboration-invites/*
router.include_router(collaboration_save_router, prefix="/collaboration")  # /collaboration/*
router.include_router(team_collaboration_router, prefix="/admin/team")  # /admin/team/*
router.include_router(team_comments_router, prefix="/team/comments")  # /team/comments/*
router.include_router(yjs_collaboration_router, prefix="/yjs")  # /yjs/* - Yjs实时协作
