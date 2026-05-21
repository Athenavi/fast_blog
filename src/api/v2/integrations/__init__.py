"""
集成API聚合路由器 - V2统一入口
整合V1的integrations相关模块
"""
from fastapi import APIRouter

# 导入V1的integrations子模块
from src.api.v1.integrations.baidu_analytics import router as baidu_analytics_router
from src.api.v1.integrations.ipfs import router as ipfs_router
from src.api.v1.integrations.oauth_login import router as oauth_login_router
from src.api.v1.integrations.sso import router as sso_router
from src.api.v1.integrations.wordpress_import import router as wordpress_import_router

# 创建聚合路由器
router = APIRouter(tags=["integrations"])

# 按顺序包含子路由
router.include_router(baidu_analytics_router, prefix="/analytics/baidu")  # /analytics/baidu/*
router.include_router(ipfs_router, prefix="/ipfs")  # /ipfs/*
router.include_router(oauth_login_router, prefix="/oauth")  # /oauth/*
router.include_router(wordpress_import_router, prefix="/wordpress")  # /wordpress/*
router.include_router(sso_router, prefix="/sso")  # /sso/* - SSO单点登录
