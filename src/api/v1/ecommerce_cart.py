"""
电子商务 API - 购物车和订单管理
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from shared.models import Cart, CartItem, Order, OrderItem, Product, User
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["ecommerce"])


# ==================== 购物车 API ====================

@router.get("/cart")
async def get_cart(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户购物车
    """
    try:
        # 查找或创建购物车
        query = select(Cart).where(Cart.user_id == current_user.id)
        result = await db.execute(query)
        cart = result.scalar_one_or_none()

        if not cart:
            # 创建新购物车
            cart = Cart(user_id=current_user.id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)

        # 获取购物车项
        items_query = (
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.cart_id == cart.id)
        )
        items_result = await db.execute(items_query)
        items = items_result.all()

        cart_items = []
        total_amount = 0

        for cart_item, product in items:
            item_total = float(product.price) * cart_item.quantity
            total_amount += item_total

            cart_items.append({
                "id": cart_item.id,
                "product": product.to_dict(),
                "quantity": cart_item.quantity,
                "price": float(product.price),
                "total": item_total
            })

        return ApiResponse(
            success=True,
            data={
                "cart_id": cart.id,
                "items": cart_items,
                "total_amount": total_amount,
                "item_count": len(cart_items)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cart/items")
async def add_to_cart(
        item_data: dict,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    添加商品到购物车
    
    Args:
        item_data: {"product_id": 1, "quantity": 2}
    """
    try:
        product_id = item_data.get("product_id")
        quantity = item_data.get("quantity", 1)

        # 验证商品
        product_query = select(Product).where(
            Product.id == product_id,
            Product.is_active == True
        )
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        if not product:
            return ApiResponse(success=False, error="商品不存在或已下架", data=None)

        # 检查库存
        if product.stock < quantity:
            return ApiResponse(success=False, error=f"库存不足,当前库存: {product.stock}", data=None)

        # 查找或创建购物车
        cart_query = select(Cart).where(Cart.user_id == current_user.id)
        cart_result = await db.execute(cart_query)
        cart = cart_result.scalar_one_or_none()

        if not cart:
            cart = Cart(user_id=current_user.id)
            db.add(cart)
            await db.flush()

        # 检查是否已存在该商品
        existing_query = select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        )
        existing_result = await db.execute(existing_query)
        existing_item = existing_result.scalar_one_or_none()

        if existing_item:
            # 更新数量
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.now()
        else:
            # 创建新购物车项
            new_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
                price=float(product.price)
            )
            db.add(new_item)

        await db.commit()

        return ApiResponse(
            success=True,
            message="已添加到购物车"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cart/items/{item_id}")
async def update_cart_item(
        item_id: int,
        item_data: dict,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新购物车项数量
    """
    try:
        quantity = item_data.get("quantity")

        if quantity is None or quantity < 1:
            return ApiResponse(success=False, error="无效的数量", data=None)

        # 查找购物车项
        query = (
            select(CartItem)
            .join(Cart, CartItem.cart_id == Cart.id)
            .where(
                CartItem.id == item_id,
                Cart.user_id == current_user.id
            )
        )
        result = await db.execute(query)
        cart_item = result.scalar_one_or_none()

        if not cart_item:
            return ApiResponse(success=False, error="购物车项不存在", data=None)

        # 检查库存
        product_query = select(Product).where(Product.id == cart_item.product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        if product and product.stock < quantity:
            return ApiResponse(success=False, error=f"库存不足,当前库存: {product.stock}", data=None)

        cart_item.quantity = quantity
        cart_item.updated_at = datetime.now()

        await db.commit()

        return ApiResponse(success=True, message="购物车项已更新")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cart/items/{item_id}")
async def remove_from_cart(
        item_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从购物车移除商品
    """
    try:
        query = (
            select(CartItem)
            .join(Cart, CartItem.cart_id == Cart.id)
            .where(
                CartItem.id == item_id,
                Cart.user_id == current_user.id
            )
        )
        result = await db.execute(query)
        cart_item = result.scalar_one_or_none()

        if not cart_item:
            return ApiResponse(success=False, error="购物车项不存在", data=None)

        await db.delete(cart_item)
        await db.commit()

        return ApiResponse(success=True, message="已从购物车移除")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 订单 API ====================

@router.post("/orders")
async def create_order(
        order_data: dict,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建订单
    
    Args:
        order_data: {
            "shipping_address": {...},
            "billing_address": {...},
            "notes": "备注"
        }
    """
    try:
        # 获取购物车
        cart_query = select(Cart).where(Cart.user_id == current_user.id)
        cart_result = await db.execute(cart_query)
        cart = cart_result.scalar_one_or_none()

        if not cart:
            return ApiResponse(success=False, error="购物车为空", data=None)

        # 获取购物车项
        items_query = (
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.cart_id == cart.id)
        )
        items_result = await db.execute(items_query)
        items = items_result.all()

        if not items:
            return ApiResponse(success=False, error="购物车为空", data=None)

        # 计算总金额
        total_amount = 0
        order_items = []

        for cart_item, product in items:
            item_total = float(product.price) * cart_item.quantity
            total_amount += item_total

            order_items.append({
                "product": product,
                "quantity": cart_item.quantity,
                "price": float(product.price),
                "total": item_total
            })

        # 生成订单号
        import uuid
        order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"

        # 创建订单
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            status="pending",
            payment_status="pending",
            total_amount=total_amount,
            shipping_amount=0,
            discount_amount=0,
            shipping_address=order_data.get("shipping_address"),
            billing_address=order_data.get("billing_address"),
            notes=order_data.get("notes")
        )

        db.add(order)
        await db.flush()

        # 创建订单项
        for item_data in order_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product"].id,
                product_name=item_data["product"].name,
                quantity=item_data["quantity"],
                price=item_data["price"],
                total=item_data["total"]
            )
            db.add(order_item)

            # 减少库存
            item_data["product"].stock -= item_data["quantity"]

        # 清空购物车
        cart_items_query = select(CartItem).where(CartItem.cart_id == cart.id)
        cart_items_result = await db.execute(cart_items_query)
        cart_items = cart_items_result.scalars().all()

        for cart_item in cart_items:
            await db.delete(cart_item)

        await db.commit()
        await db.refresh(order)

        return ApiResponse(
            success=True,
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "total_amount": order.total_amount
            },
            message="订单创建成功"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def list_orders(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(10, ge=1, le=100, description="每页数量"),
        status: Optional[str] = Query(None, description="订单状态"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户订单列表
    """
    try:
        query = select(Order).where(Order.user_id == current_user.id)

        if status:
            query = query.where(Order.status == status)

        query = query.order_by(Order.created_at.desc())

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await db.execute(query)
        orders = result.scalars().all()

        orders_data = [order.to_dict() for order in orders]

        return ApiResponse(
            success=True,
            data={
                "orders": orders_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": (total + per_page - 1) // per_page
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(
        order_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取订单详情
    """
    try:
        query = select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            return ApiResponse(success=False, error="订单不存在", data=None)

        # 获取订单项
        items_query = (
            select(OrderItem, Product)
            .outerjoin(Product, OrderItem.product_id == Product.id)
            .where(OrderItem.order_id == order.id)
        )
        items_result = await db.execute(items_query)
        items = items_result.all()

        order_items = []
        for order_item, product in items:
            item_data = order_item.to_dict()
            if product:
                item_data["product"] = product.to_dict()
            order_items.append(item_data)

        order_data = order.to_dict()
        order_data["items"] = order_items

        return ApiResponse(success=True, data=order_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
