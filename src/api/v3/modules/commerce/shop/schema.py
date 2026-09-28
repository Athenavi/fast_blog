"""商城模块请求模型（商品 / 购物车 / 订单）"""

from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class ProductCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    price: float = Field(ge=0)
    original_price: Optional[float] = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    sku: Optional[str] = Field(default=None, max_length=100)
    category_id: Optional[int] = None
    is_active: bool = True
    is_featured: bool = False


class ProductUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, max_length=100)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class StockAdjustRequest(SchemaBase):
    """库存调整（正数入库、负数出库；出库不允许扣成负数）"""

    delta: int = Field(description="增减量，如 +10 / -3")


class CartAddRequest(SchemaBase):
    product_id: int = Field(ge=1)
    quantity: int = Field(default=1, ge=1, le=9999)


class CartItemUpdateRequest(SchemaBase):
    quantity: int = Field(ge=1, le=9999)


class OrderItemRequest(SchemaBase):
    product_id: int = Field(ge=1)
    quantity: int = Field(default=1, ge=1, le=9999)


class OrderCreateRequest(SchemaBase):
    """下单请求：``from_cart=True`` 用购物车结算，否则用 ``items`` 直接下单"""

    from_cart: bool = Field(default=False, description="true=结算购物车")
    items: Optional[List[OrderItemRequest]] = Field(default=None, description="直接下单的商品明细")
    session_id: Optional[str] = Field(default=None, max_length=255, description="匿名购物车会话 ID")
    shipping_amount: float = Field(default=0, ge=0)
    discount_amount: float = Field(default=0, ge=0)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    shipping_address: Optional[str] = Field(default=None, max_length=500)
    billing_address: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)


class OrderPaidRequest(SchemaBase):
    transaction_id: Optional[str] = Field(default=None, max_length=100)


class OrderRefundRequest(SchemaBase):
    restore_stock: bool = Field(default=False, description="退货退款时同时回滚库存")
    reason: Optional[str] = Field(default=None, max_length=255)


class CartQuery(SchemaBase):
    session_id: Optional[str] = Field(default=None, max_length=255, description="未登录时用会话 ID 定位购物车")
