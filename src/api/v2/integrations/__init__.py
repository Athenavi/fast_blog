"""
集成API聚合路由器 - V2统一入口
整合V1的integrations相关模块

使用懒加载模式：仅在首次访问 router 时才导入 V1 子模块。
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["integrations"])

    from src.api.v2.integrations.baidu_analytics import router as baidu_analytics_router
    from src.api.v2.integrations.google_analytics import router as google_analytics_router
    from src.api.v2.integrations.ipfs import router as ipfs_router
    from src.api.v2.integrations.oauth_login import router as oauth_login_router
    from src.api.v2.integrations.sso import router as sso_router
    from src.api.v2.integrations.wordpress_import import router as wordpress_import_router
    from src.api.v2.integrations.session_policy import router as session_policy_router
    from src.api.v2.integrations.scim import router as scim_router
    from src.api.v2.integrations.jekyll_import import router as jekyll_router
    from src.api.v2.integrations.hexo_import import router as hexo_router
    from src.api.v2.integrations.ghost_import import router as ghost_router
    from src.api.v2.integrations.medium_import import router as medium_router
    from src.api.v2.integrations.health_check import router as health_check_router

    router.include_router(baidu_analytics_router, prefix="/analytics/baidu")
    router.include_router(google_analytics_router, prefix="/analytics/google")
    router.include_router(ipfs_router, prefix="/ipfs")
    router.include_router(oauth_login_router, prefix="/oauth")
    router.include_router(wordpress_import_router, prefix="/wordpress")
    router.include_router(sso_router, prefix="/sso")
    router.include_router(session_policy_router)
    router.include_router(scim_router)
    router.include_router(jekyll_router, prefix="/import/jekyll")
    router.include_router(hexo_router, prefix="/import/hexo")
    router.include_router(ghost_router, prefix="/import/ghost")
    router.include_router(medium_router, prefix="/import/medium")
    router.include_router(health_check_router, prefix="/health")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
