"""
高级功能API聚合路由器 - V2统一入口
整合V1的advanced_features相关模块
"""
from fastapi import APIRouter

from src.api.v1.advanced_features.achievement_badges import router as achievement_badges_router
from src.api.v1.advanced_features.ai_recommendations import router as ai_recommendations_router
from src.api.v1.advanced_features.edge_functions import router as edge_functions_router
from src.api.v1.advanced_features.expert_certification import router as expert_certification_router
# 导入V1的advanced_features子模块
from src.api.v1.advanced_features.membership import router as membership_router
from src.api.v1.advanced_features.nft import router as nft_router
from src.api.v1.advanced_features.personalized_feed import router as personalized_feed_router
from src.api.v1.advanced_features.points_system import router as points_system_router
from src.api.v1.advanced_features.recommendations import router as recommendations_router
from src.api.v1.advanced_features.tipping_system import router as tipping_system_router
from src.api.v1.advanced_features.websocket import router as websocket_router

# 创建聚合路由器
router = APIRouter(tags=["advanced-features"])

# 按顺序包含子路由
router.include_router(membership_router, prefix="/membership")  # /ext/membership/*
router.include_router(edge_functions_router, prefix="/edge—func")  # /ext/edge—func/*
router.include_router(achievement_badges_router, prefix="/badges")  # /ext/badges/*
router.include_router(ai_recommendations_router, prefix="/ai-recommendations")  # /ext/ai-recommendations/*
router.include_router(expert_certification_router, prefix="/expert-certification")  # /ext/expert-certification/*
router.include_router(nft_router, prefix="/nft")  # /ext/nft/*
router.include_router(personalized_feed_router, prefix="/personalized-feed")  # /ext/personalized-feed/*
router.include_router(points_system_router, prefix="/point-system")  # /ext/point-system/*
router.include_router(recommendations_router, prefix="/recommendations")  # /ext/recommendations/*
router.include_router(tipping_system_router, prefix="/tipping-system")  # /ext/tipping-system/*
router.include_router(websocket_router, prefix="/ws")  # /ext/ws/*
