"""
插件API - V2 统一入口
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["plugins"])

    from src.api.v2.plugins.plugin_management import router as plugin_management_router
    from src.api.v2.plugins.article_rating import router as article_rating_router

    router.include_router(plugin_management_router, prefix="")
    router.include_router(article_rating_router, prefix="")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
