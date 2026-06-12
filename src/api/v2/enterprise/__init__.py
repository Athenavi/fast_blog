"""
企业功能API - V2 统一入口
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["enterprise-v2"])

    from src.api.v2.enterprise.enterprise_api import router as enterprise_router
    from src.api.v2.enterprise.admin_endpoints import router as admin_router
    router.include_router(enterprise_router)
    router.include_router(admin_router, prefix="/admin")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
