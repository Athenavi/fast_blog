"""
可访问性API - V2 统一入口
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["accessibility-v2"])

    from src.api.v2.accessibility.accessibility_audit import router as accessibility_audit_router
    from src.api.v2.accessibility.amp import router as amp_router

    router.include_router(accessibility_audit_router, prefix="/audit")
    router.include_router(amp_router, prefix="/amp")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
