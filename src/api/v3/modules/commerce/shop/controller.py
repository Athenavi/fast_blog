"""commerce/shop 模块路由（商品 / 购物车 / 订单 / 库存）

**商品与库存（管理端）**::

    GET    /api/v3/commerce/shop/products                商品列表
    POST   /api/v3/commerce/shop/products                新建商品
    GET    /api/v3/commerce/shop/products/low-stock      低库存/售罄（静态路径前置）
    GET    /api/v3/commerce/shop/products/{product_id}   商品详情
    PUT    /api/v3/commerce/shop/products/{product_id}   更新商品
    DELETE /api/v3/commerce/shop/products/{product_id}   删除（有订单引用时改为下架）
    POST   /api/v3/commerce/shop/products/{product_id}/stock  库存增减

**购物车（登录用户；也支持匿名 session_id）**::

    GET    /api/v3/commerce/shop/cart                    查看购物车
    POST   /api/v3/commerce/shop/cart/items              加入购物车
    PUT    /api/v3/commerce/shop/cart/items/{item_id}    修改数量
    DELETE /api/v3/commerce/shop/cart/items/{item_id}    移除项
    DELETE /api/v3/commerce/shop/cart                    清空购物车

**订单**::

    POST   /api/v3/commerce/shop/orders                  下单（购物车结算 / 直接下单）
    GET    /api/v3/commerce/shop/orders                  订单列表（管理端带数据范围过滤）
    GET    /api/v3/commerce/shop/orders/stats            订单统计
    GET    /api/v3/commerce/shop/orders/{order_id}       订单详情（含明细）
    POST   /api/v3/commerce/shop/orders/{order_id}/pay       标记已支付
    POST   /api/v3/commerce/shop/orders/{order_id}/ship      标记发货
    POST   /api/v3/commerce/shop/orders/{order_id}/deliver   标记收货
    POST   /api/v3/commerce/shop/orders/{order_id}/cancel    取消（回滚库存）
    POST   /api/v3/commerce/shop/orders/{order_id}/refund    退款（可选回滚库存）

权限：商品与订单管理复用 ``payment:view/create/edit/delete`` 与 ``revenue:edit``（不新增权限码）；
购物车与下单仅需登录（普通用户即可），管理端订单列表按 ``data_scope`` 过滤。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.commerce.shop.schema import (
    CartAddRequest,
    CartItemUpdateRequest,
    OrderCreateRequest,
    OrderPaidRequest,
    OrderRefundRequest,
    ProductCreate,
    ProductUpdate,
    StockAdjustRequest,
)
from src.api.v3.modules.commerce.shop.service import shop_service

router = APIRouter(prefix="/shop", tags=["commerce-shop"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 商品
@router.get("/products", response_model=ResponseModel, summary="商品列表")
async def list_products(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await shop_service.list_products(
        db, page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/products/low-stock", response_model=ResponseModel, summary="低库存 / 售罄商品")
async def low_stock_products(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    threshold: int = Query(default=5, ge=0, le=1000),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return resp.success(await shop_service.low_stock(db, threshold=threshold, limit=limit))


@router.post("/products", response_model=ResponseModel, summary="新建商品")
async def create_product(
    payload: ProductCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_CREATE),
) -> dict:
    return resp.success(
        await shop_service.create_product(db, payload.model_dump(exclude_unset=True)), msg="已创建"
    )


@router.get("/products/{product_id}", response_model=ResponseModel, summary="商品详情")
async def get_product(
    product_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
) -> dict:
    return resp.success(await shop_service.get_product(db, product_id))


@router.put("/products/{product_id}", response_model=ResponseModel, summary="更新商品")
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await shop_service.update_product(db, product_id, payload.model_dump(exclude_unset=True)),
        msg="已更新",
    )


@router.delete("/products/{product_id}", response_model=ResponseModel, summary="删除商品")
async def delete_product(
    product_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_DELETE),
) -> dict:
    await shop_service.delete_product(db, product_id)
    return resp.success(None, msg="已删除或下架（存在订单引用时改为下架）")


@router.post("/products/{product_id}/stock", response_model=ResponseModel, summary="库存增减")
async def adjust_product_stock(
    product_id: int,
    payload: StockAdjustRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await shop_service.adjust_stock(db, product_id, payload.delta), msg="库存已更新"
    )


# ---------------------------------------------------------------- 购物车
def _cart_owner(current: CurrentUser, session_id: Optional[str]) -> dict:
    return {"user_id": getattr(current, "id", None), "session_id": session_id}


@router.get("/cart", response_model=ResponseModel, summary="查看购物车")
async def view_cart(
    db: DBSession,
    current: CurrentUser,
    session_id: Optional[str] = Query(default=None, description="匿名会话 ID（未登录时使用）"),
) -> dict:
    return resp.success(await shop_service.view_cart(db, **_cart_owner(current, session_id)))


@router.post("/cart/items", response_model=ResponseModel, summary="加入购物车")
async def add_cart_item(
    payload: CartAddRequest,
    db: DBSession,
    current: CurrentUser,
    session_id: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await shop_service.add_to_cart(
            db,
            product_id=payload.product_id,
            quantity=payload.quantity,
            **_cart_owner(current, session_id),
        ),
        msg="已加入购物车",
    )


@router.put("/cart/items/{item_id}", response_model=ResponseModel, summary="修改购物车项数量")
async def update_cart_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    db: DBSession,
    current: CurrentUser,
    session_id: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await shop_service.update_cart_item(
            db, item_id, quantity=payload.quantity, **_cart_owner(current, session_id)
        ),
        msg="已更新",
    )


@router.delete("/cart/items/{item_id}", response_model=ResponseModel, summary="移除购物车项")
async def remove_cart_item(
    item_id: int,
    db: DBSession,
    current: CurrentUser,
    session_id: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await shop_service.remove_cart_item(db, item_id, **_cart_owner(current, session_id)),
        msg="已移除",
    )


@router.delete("/cart", response_model=ResponseModel, summary="清空购物车")
async def clear_cart(
    db: DBSession,
    current: CurrentUser,
    session_id: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await shop_service.clear_cart(db, **_cart_owner(current, session_id)), msg="已清空"
    )


# ---------------------------------------------------------------- 订单
@router.post("/orders", response_model=ResponseModel, summary="下单")
async def create_order(
    payload: OrderCreateRequest,
    db: DBSession,
    current: CurrentUser,
) -> dict:
    """下单会**真实扣减库存**并写入订单与明细；购物车结算后自动清空对应项"""
    return resp.success(
        await shop_service.create_order(
            db,
            user_id=getattr(current, "id"),
            payload=payload.model_dump(exclude_unset=True),
            session_id=payload.session_id,
        ),
        msg="下单成功",
    )


@router.get("/orders", response_model=ResponseModel, summary="订单列表")
async def list_orders(
    db: DBSession,
    current: CurrentUser,
    page: PageDep,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    user_id: Optional[int] = Query(default=None),
) -> dict:
    """管理端列表：按当前用户 ``data_scope`` 过滤（仅本人 / 本组 / 全部 / 自定义组）"""
    items, total = await shop_service.list_orders(
        db,
        page=page.page,
        page_size=page.page_size,
        status=status_filter,
        user_id=user_id,
        scope_user=current,
    )
    return resp.success_page(items, total, page.page, page.page_size)


@router.get("/orders/stats", response_model=ResponseModel, summary="订单统计")
async def order_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return resp.success(await shop_service.order_stats(db, days=days))


@router.get("/orders/{order_id}", response_model=ResponseModel, summary="订单详情（含明细）")
async def get_order(
    order_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_VIEW),
) -> dict:
    return resp.success(await shop_service.get_order(db, order_id, scope_user=current))


@router.post("/orders/{order_id}/pay", response_model=ResponseModel, summary="标记已支付")
async def mark_order_paid(
    order_id: int,
    payload: OrderPaidRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await shop_service.mark_paid(
            db, order_id, transaction_id=payload.transaction_id, scope_user=current
        ),
        msg="已标记支付",
    )


@router.post("/orders/{order_id}/ship", response_model=ResponseModel, summary="标记发货")
async def mark_order_shipped(
    order_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(await shop_service.mark_shipped(db, order_id, scope_user=current), msg="已发货")


@router.post("/orders/{order_id}/deliver", response_model=ResponseModel, summary="标记收货")
async def mark_order_delivered(
    order_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(
        await shop_service.mark_delivered(db, order_id, scope_user=current), msg="已确认收货"
    )


@router.post("/orders/{order_id}/cancel", response_model=ResponseModel, summary="取消订单（回滚库存）")
async def cancel_order(
    order_id: int,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.PAYMENT_EDIT),
) -> dict:
    return resp.success(await shop_service.cancel_order(db, order_id, scope_user=current), msg="已取消")


@router.post("/orders/{order_id}/refund", response_model=ResponseModel, summary="退款")
async def refund_order(
    order_id: int,
    payload: OrderRefundRequest,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.REVENUE_EDIT),
) -> dict:
    return resp.success(
        await shop_service.refund_order(
            db,
            order_id,
            restore_stock=payload.restore_stock,
            reason=payload.reason,
            scope_user=current,
        ),
        msg="已退款",
    )
