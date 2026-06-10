"""
广告营销API - V2 统一入口
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["marketing-v2"])

    from src.api.v2.marketing.ad_management import router as ad_management_router
    from src.api.v2.marketing.advertisement_system import router as advertisement_system_router

    router.include_router(ad_management_router, prefix="/management")
    router.include_router(advertisement_system_router, prefix="/system")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
