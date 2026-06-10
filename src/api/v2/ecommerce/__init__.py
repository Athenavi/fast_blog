"""
电商模块 - V2 统一入口
整合所有电商相关功能

使用懒加载模式：仅在首次访问 router 时才导入 V1 子模块。
"""
from fastapi import APIRouter

_router = None


def _build_router():
    global _router
    if _router is not None:
        return _router

    router = APIRouter(tags=["ecommerce-v2"])

    from src.api.v2.ecommerce.ecommerce import router as ecommerce_router
    from src.api.v2.ecommerce.ecommerce_cart import router as ecommerce_cart_router
    from src.api.v2.ecommerce.ecommerce_orders import router as ecommerce_orders_router
    from src.api.v2.ecommerce.inventory_management import router as inventory_management_router
    from src.api.v2.ecommerce.revenue_sharing import router as revenue_sharing_router
    from src.api.v2.utils.payment import router as payment_router
    from src.api.v2.payment.payment_management import router as payment_management_router

    router.include_router(ecommerce_router, prefix="/products")
    router.include_router(ecommerce_cart_router, prefix="/cart")
    router.include_router(ecommerce_orders_router, prefix="/orders")
    router.include_router(inventory_management_router, prefix="/inventory")
    router.include_router(revenue_sharing_router, prefix="/revenue")
    router.include_router(payment_router, prefix="/payment")
    router.include_router(payment_management_router, prefix="/admin")

    _router = router
    return _router


def __getattr__(name):
    if name == "router":
        return _build_router()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
