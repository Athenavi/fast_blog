"""
电子商务 API - 购物车和订单管理
"""
from datetime import datetime
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Cart, CartItem, Product
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["ecommerce"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


# ==================== 购物车 API ====================

@router.get("")
@_catch
async def get_cart(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户购物车
    """
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

    return ok(data={
        "cart_id": cart.id,
        "items": cart_items,
        "total_amount": total_amount,
        "item_count": len(cart_items)
    })


@router.post("/items")
@_catch
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
        return fail("商品不存在或已下架")

    # 检查库存
    if product.stock < quantity:
        return fail(f"库存不足,当前库存: {product.stock}")

    # 查找或创建购物车
    cart_query = select(Cart).where(Cart.user_id == current_user.id)
    cart_result = await db.execute(cart_query)
    cart = cart_result.scalar_one_or_none()

    try:
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
    except Exception:
        await db.rollback()
        raise

    return ok(msg="已添加到购物车")


@router.put("/items/{item_id}")
@_catch
async def update_cart_item(
        item_id: int,
        item_data: dict,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新购物车项数量
    """
    quantity = item_data.get("quantity")

    if quantity is None or quantity < 1:
        return fail("无效的数量")

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
        return fail("购物车项不存在")

    # 检查库存
    product_query = select(Product).where(Product.id == cart_item.product_id)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if product and product.stock < quantity:
        return fail(f"库存不足,当前库存: {product.stock}")

    try:
        cart_item.quantity = quantity
        cart_item.updated_at = datetime.now()

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="购物车项已更新")


@router.delete("/items/{item_id}")
@_catch
async def remove_from_cart(
        item_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从购物车移除商品
    """
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
        return fail("购物车项不存在")

    try:
        await db.delete(cart_item)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="已从购物车移除")
