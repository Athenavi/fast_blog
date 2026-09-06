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

    router.include_router(plugin_management_router, prefix="")
    # 注意：主题路由已在 v2/__init__.py 中单独注册为 /api/v2/themes
    # 不需要在此处重复注册

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    # 允许访问子模块（如 theme_routes）
    import importlib
    try:
        return importlib.import_module(f"{__package__}.{name}")
    except ModuleNotFoundError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
