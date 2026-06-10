"""
统计分析API - V2 统一入口
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["analytics"])

    from src.api.v2.analytics.site_analytics_api import router as site_analytics_router
    router.include_router(site_analytics_router)

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
