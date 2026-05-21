"""
电商模块 - V2 统一入口
整合所有电商相关功能：商品、购物车、订单、库存、收益分成等

采用包级别聚合模式，所有子模块通过此文件统一注册
"""
from fastapi import APIRouter

# 导入所有电商子模块路由（从 V1 迁移）
from src.api.v1.ecommerce.ecommerce import router as ecommerce_router
from src.api.v1.ecommerce.ecommerce_cart import router as ecommerce_cart_router
from src.api.v1.ecommerce.ecommerce_orders import router as ecommerce_orders_router
from src.api.v1.ecommerce.inventory_management import router as inventory_management_router
from src.api.v1.ecommerce.revenue_sharing import router as revenue_sharing_router

router = APIRouter(tags=["ecommerce-v2"])

# 包含所有电商子路由
router.include_router(ecommerce_router, prefix="/products")  # /products/* - 商品管理
router.include_router(ecommerce_cart_router, prefix="/cart")  # /cart/* - 购物车
router.include_router(ecommerce_orders_router, prefix="/orders")  # /orders/* - 订单管理
router.include_router(inventory_management_router, prefix="/inventory")  # /inventory/* - 库存管理
router.include_router(revenue_sharing_router, prefix="/revenue")  # /revenue/* - 收益分成
