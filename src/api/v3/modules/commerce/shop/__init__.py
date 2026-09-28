"""commerce/shop：商品 / 购物车 / 订单 / 库存（全部落在既有 ecommerce 表上）

对应 v2 的 ``payment/order_management``（内存对象模型）与 ``ecommerce/inventory_service``，
v3 直接用 ``products`` / ``carts`` / ``cart_items`` / ``orders`` / ``order_items`` 真表实现，
不新增表（``products.stock`` 即库存字段）。
"""

from src.api.v3.modules.commerce.shop.service import shop_service

__all__ = ["shop_service"]
