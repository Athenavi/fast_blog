"""商城：商品 / 购物车 / 订单 / 库存（v3 真实实现）

替代 v2 的 ``shared/services/payment/order_management.py``（659 行，Order/Cart/OrderItem
内存对象模型）与 ``shared/services/ecommerce/inventory_service.py``（386 行）。

与 v2 的关键差别：v2 用 **Python 对象 + 内存字典** 表示订单与库存（重启即丢、无法跨进程），
v3 直接用**已存在的真表**（``products`` / ``carts`` / ``cart_items`` / ``orders`` /
``order_items``，其中 ``products.stock`` 即库存字段），不新增表。

流程要点（全部真实落库）：

  - **加购**：校验商品存在且上架、库存充足；同商品累加数量
  - **下单**：逐项再次校验库存 → 扣减 ``products.stock`` → 写 ``orders`` + ``order_items``
    → 清空已下单的购物车项；订单号 ``ORD{日期}{随机}`` 唯一
  - **取消**：回滚库存（只回滚未发货的订单）
  - **状态机**：pending → paid → shipped → delivered（可 cancel）；``paid_at`` / ``shipped_at``
    / ``delivered_at`` 与 ``payment_status`` 同步
"""

import secrets
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.ecommerce.cart import Cart
from shared.models.ecommerce.cart_item import CartItem
from shared.models.ecommerce.order import Order
from shared.models.ecommerce.order_item import OrderItem
from shared.models.ecommerce.product import Product
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("commerce.shop")

#: 订单状态机（可流转的目标）
ORDER_STATUSES = ("pending", "paid", "shipped", "delivered", "cancelled", "refunded")
#: 只有这些状态可以取消（未发货）
CANCELLABLE = ("pending", "paid")
#: 已结算的订单状态（计入商城统计）
SETTLED = ("paid", "shipped", "delivered")

_CENTS = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def _new_order_number() -> str:
    return f"ORD{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(3).upper()}"


class ShopService:
    """商品 / 购物车 / 订单 / 库存"""

    # ------------------------------------------------------------------ 商品
    async def list_products(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        conditions = []
        if keyword:
            like = f"%{keyword}%"
            conditions.append(or_(Product.name.like(like), Product.sku.like(like)))
        if is_active is not None:
            conditions.append(Product.is_active.is_(is_active))

        total = int(
            (await db.execute(select(func.count()).select_from(Product).where(*conditions))).scalar()
            or 0
        )
        rows = (
            await db.execute(
                select(Product)
                .where(*conditions)
                .order_by(Product.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return [self._product_out(row) for row in rows], total

    async def get_product(self, db: AsyncSession, product_id: int) -> Dict[str, Any]:
        row = await db.get(Product, product_id)
        if row is None:
            raise NotFoundError("商品不存在")
        return self._product_out(row)

    async def create_product(self, db: AsyncSession, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now()
        row = Product(
            name=data["name"],
            slug=data.get("slug") or f"p-{secrets.token_hex(4)}",
            description=data.get("description"),
            price=_money(data.get("price")),
            original_price=_money(data["original_price"]) if data.get("original_price") else None,
            stock=int(data.get("stock") or 0),
            sku=data.get("sku"),
            category_id=data.get("category_id"),
            is_active=bool(data.get("is_active", True)),
            is_featured=bool(data.get("is_featured", False)),
            created_at=now,
            updated_at=now,
        )
        if row.stock < 0:
            raise BadRequestError("库存不能为负")
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return self._product_out(row)

    async def update_product(
        self, db: AsyncSession, product_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        row = await db.get(Product, product_id)
        if row is None:
            raise NotFoundError("商品不存在")
        for field in ("name", "slug", "description", "sku", "category_id", "is_active", "is_featured"):
            if field in data and data[field] is not None:
                setattr(row, field, data[field])
        if data.get("price") is not None:
            row.price = _money(data["price"])
        if data.get("stock") is not None:
            stock = int(data["stock"])
            if stock < 0:
                raise BadRequestError("库存不能为负")
            row.stock = stock
        row.updated_at = datetime.now()
        await db.commit()
        await db.refresh(row)
        return self._product_out(row)

    async def delete_product(self, db: AsyncSession, product_id: int) -> None:
        row = await db.get(Product, product_id)
        if row is None:
            raise NotFoundError("商品不存在")
        in_orders = (
                        await db.execute(
                            select(func.count()).select_from(OrderItem).where(OrderItem.product_id == product_id)
                        )
                    ).scalar() or 0
        if in_orders:
            # 有历史订单引用：下架而不是物理删除，避免破坏订单明细
            row.is_active = False
            row.updated_at = datetime.now()
            await db.commit()
            return
        await db.delete(row)
        await db.commit()

    # ------------------------------------------------------------------ 库存
    async def stock_check(self, db: AsyncSession, items: Sequence[Tuple[int, int]]) -> List[Dict[str, Any]]:
        """逐项校验库存（返回每项的可用性与缺口，不写库）"""
        result: List[Dict[str, Any]] = []
        for product_id, quantity in items:
            product = await db.get(Product, product_id)
            if product is None:
                result.append({"product_id": product_id, "ok": False, "reason": "商品不存在"})
                continue
            stock = int(product.stock or 0)
            ok = bool(product.is_active) and stock >= int(quantity)
            reason = None
            if not product.is_active:
                reason = "商品已下架"
            elif stock < int(quantity):
                reason = f"库存不足（剩余 {stock}，需要 {quantity}）"
            result.append({
                "product_id": product_id,
                "name": product.name,
                "ok": ok,
                "available": stock,
                "requested": int(quantity),
                "reason": reason,
            })
        return result

    async def adjust_stock(self, db: AsyncSession, product_id: int, delta: int) -> Dict[str, Any]:
        """库存增减（``delta`` 可正可负；扣到负数会拒绝）"""
        product = await db.get(Product, product_id)
        if product is None:
            raise NotFoundError("商品不存在")
        new_stock = int(product.stock or 0) + int(delta)
        if new_stock < 0:
            raise ConflictError(f"库存不足：当前 {product.stock}，需要减少 {abs(int(delta))}")
        product.stock = new_stock
        product.updated_at = datetime.now()
        await db.commit()
        await db.refresh(product)
        return {"product_id": product.id, "name": product.name, "stock": int(product.stock)}

    async def low_stock(self, db: AsyncSession, *, threshold: int = 5, limit: int = 50) -> Dict[str, Any]:
        """低库存商品（含售罄），供补货看板"""
        rows = (
            await db.execute(
                select(Product)
                .where(Product.is_active.is_(True), Product.stock <= threshold)
                .order_by(Product.stock.asc(), Product.id.asc())
                .limit(limit)
            )
        ).scalars().all()
        return {
            "threshold": threshold,
            "items": [
                {"id": row.id, "name": row.name, "sku": row.sku, "stock": int(row.stock or 0)}
                for row in rows
            ],
        }

    # ------------------------------------------------------------------ 购物车
    async def _get_or_create_cart(
        self, db: AsyncSession, *, user_id: Optional[int], session_id: Optional[str]
    ) -> Cart:
        if user_id is None and not session_id:
            raise BadRequestError("需要 user_id 或 session_id 之一")
        conditions = [Cart.user_id == user_id] if user_id is not None else [Cart.session_id == session_id]
        cart = (await db.execute(select(Cart).where(*conditions).order_by(Cart.id.desc()))).scalars().first()
        if cart is None:
            now = datetime.now()
            cart = Cart(user_id=user_id, session_id=session_id, created_at=now, updated_at=now)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
        return cart

    async def view_cart(
        self, db: AsyncSession, *, user_id: Optional[int] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """购物车内容（含每项小计与合计）"""
        cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
        return await self._cart_out(db, cart)

    async def add_to_cart(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        quantity: int = 1,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """加入购物车（同商品累加；库存不足直接拒绝）"""
        if quantity < 1:
            raise BadRequestError("数量必须大于 0")
        cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
        checks = await self.stock_check(db, [(product_id, quantity)])
        if not checks[0]["ok"]:
            raise ConflictError(checks[0]["reason"] or "库存不足")

        item = (
            await db.execute(
                select(CartItem).where(
                    CartItem.cart_id == cart.id, CartItem.product_id == product_id
                )
            )
        ).scalars().first()
        product = await db.get(Product, product_id)
        if item is None:
            now = datetime.now()
            db.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=product_id,
                    quantity=int(quantity),
                    price=_money(product.price),
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            new_quantity = int(item.quantity or 0) + int(quantity)
            check = await self.stock_check(db, [(product_id, new_quantity)])
            if not check[0]["ok"]:
                raise ConflictError(check[0]["reason"] or "库存不足")
            item.quantity = new_quantity
            item.updated_at = datetime.now()
        cart.updated_at = datetime.now()
        await db.commit()
        logger.info("加入购物车 cart=%s product=%s qty=%s（%s）", cart.id, product_id, quantity, product.name)
        return await self._cart_out(db, cart)

    async def update_cart_item(
        self,
        db: AsyncSession,
        item_id: int,
        *,
        quantity: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        item = await db.get(CartItem, item_id)
        if item is None:
            raise NotFoundError("购物车项不存在")
        cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
        if int(item.cart_id or 0) != int(cart.id):
            raise NotFoundError("购物车项不存在")
        if quantity < 1:
            raise BadRequestError("数量必须大于 0")
        check = await self.stock_check(db, [(int(item.product_id), quantity)])
        if not check[0]["ok"]:
            raise ConflictError(check[0]["reason"] or "库存不足")
        item.quantity = int(quantity)
        item.updated_at = datetime.now()
        await db.commit()
        return await self._cart_out(db, cart)

    async def remove_cart_item(
        self,
        db: AsyncSession,
        item_id: int,
        *,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        item = await db.get(CartItem, item_id)
        if item is None:
            raise NotFoundError("购物车项不存在")
        cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
        await db.delete(item)
        await db.commit()
        return await self._cart_out(db, cart)

    async def clear_cart(
        self, db: AsyncSession, *, user_id: Optional[int] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
        await db.execute(CartItem.__table__.delete().where(CartItem.cart_id == cart.id))
        await db.commit()
        return await self._cart_out(db, cart)

    async def _cart_out(self, db: AsyncSession, cart: Cart) -> Dict[str, Any]:
        rows = (
            await db.execute(
                select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id.asc())
            )
        ).scalars().all()
        products = {
            row.id: row
            for row in (
                await db.execute(
                    select(Product).where(Product.id.in_([int(i.product_id) for i in rows]))
                )
            ).scalars().all()
        } if rows else {}

        items: List[Dict[str, Any]] = []
        total = Decimal("0")
        for item in rows:
            product = products.get(int(item.product_id))
            unit_price = _money(product.price if product else 0)
            quantity = int(item.quantity or 0)
            subtotal = _money(unit_price * quantity)
            total += subtotal
            items.append({
                "id": item.id,
                "product_id": item.product_id,
                "name": product.name if product else None,
                "unit_price": float(unit_price),
                "quantity": quantity,
                "subtotal": float(subtotal),
                "stock": int(product.stock or 0) if product else 0,
                "available": bool(product and product.is_active),
            })
        return {
            "cart_id": cart.id,
            "user_id": cart.user_id,
            "session_id": cart.session_id,
            "items": items,
            "total": float(_money(total)),
            "count": sum(item["quantity"] for item in items),
        }

    # ------------------------------------------------------------------ 订单
    async def create_order(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """下单：校验并扣减库存 → 写订单与明细 → 清空对应购物车项

        两种来源：``payload["items"]``（直接下单，元素为 ``{product_id, quantity}``）
        或购物车（``payload["from_cart"]=True``，需 ``user_id``/``session_id``）。
        """
        from_cart = bool(payload.get("from_cart"))
        if from_cart:
            cart = await self._get_or_create_cart(db, user_id=user_id, session_id=session_id)
            cart_items = (
                await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
            ).scalars().all()
            if not cart_items:
                raise BadRequestError("购物车为空，无法下单")
            requested = [(int(item.product_id), int(item.quantity or 0)) for item in cart_items]
        else:
            requested = [
                (int(item["product_id"]), int(item.get("quantity") or 1))
                for item in (payload.get("items") or [])
            ]
            if not requested:
                raise BadRequestError("下单需要 items 或 from_cart")

        checks = await self.stock_check(db, requested)
        failures = [item for item in checks if not item["ok"]]
        if failures:
            raise ConflictError("；".join(item["reason"] or "库存不足" for item in failures))

        now = datetime.now()
        order = Order(
            order_number=_new_order_number(),
            user_id=user_id,
            status="pending",
            total_amount=_money(0),
            shipping_amount=_money(payload.get("shipping_amount") or 0),
            discount_amount=_money(payload.get("discount_amount") or 0),
            payment_method=payload.get("payment_method"),
            payment_status="unpaid",
            shipping_address=payload.get("shipping_address"),
            billing_address=payload.get("billing_address"),
            notes=payload.get("notes"),
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        await db.flush()

        goods_total = Decimal("0")
        for product_id, quantity in requested:
            product = await db.get(Product, product_id)
            unit_price = _money(product.price)
            subtotal = _money(unit_price * quantity)
            goods_total += subtotal
            db.add(
                OrderItem(
                    order=order.id,
                    product_id=product_id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=subtotal,
                    created_at=now,
                    updated_at=now,
                )
            )
            product.stock = int(product.stock or 0) - quantity
            product.updated_at = now

        order.total_amount = _money(goods_total + order.shipping_amount - order.discount_amount)
        if order.total_amount < 0:
            raise BadRequestError("优惠金额不能超过商品总额")
        await db.commit()

        if from_cart:
            await db.execute(CartItem.__table__.delete().where(CartItem.cart_id == cart.id))
            await db.commit()

        logger.info("创建订单 %s（user=%s 金额=%s）", order.order_number, user_id, order.total_amount)
        return await self.get_order(db, order.id)

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        scope_user: Any = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        conditions = []
        if status:
            conditions.append(Order.status == status)
        if user_id is not None:
            conditions.append(Order.user_id == user_id)

        from src.api.v3.core.permission.scope import apply_data_scope

        count_stmt = select(func.count()).select_from(Order).where(*conditions)
        stmt = select(Order).where(*conditions)
        if scope_user is not None:
            count_stmt = await apply_data_scope(count_stmt, Order, db=db, user=scope_user)
            stmt = await apply_data_scope(stmt, Order, db=db, user=scope_user)

        total = int((await db.execute(count_stmt)).scalar() or 0)
        rows = (
            await db.execute(
                stmt.order_by(Order.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return [self._order_out(row) for row in rows], total

    async def get_order(
        self, db: AsyncSession, order_id: int, *, scope_user: Any = None
    ) -> Dict[str, Any]:
        order = await db.get(Order, order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        if scope_user is not None:
            from src.api.v3.core.permission.scope import ensure_object_in_scope

            await ensure_object_in_scope(db, Order, order, user=scope_user)

        items = (
            await db.execute(select(OrderItem).where(OrderItem.order == order.id).order_by(OrderItem.id))
        ).scalars().all()
        data = self._order_out(order)
        data["items"] = [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": int(item.quantity or 0),
                "unit_price": float(_money(item.unit_price)),
                "total_price": float(_money(item.total_price)),
            }
            for item in items
        ]
        return data

    async def _transition(
        self,
        db: AsyncSession,
        order_id: int,
        *,
        allowed: Sequence[str],
        target: str,
        scope_user: Any = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        order = await db.get(Order, order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        if scope_user is not None:
            from src.api.v3.core.permission.scope import ensure_object_in_scope

            await ensure_object_in_scope(db, Order, order, user=scope_user)
        current = str(order.status or "pending")
        if current not in allowed:
            raise ConflictError(f"订单当前状态 {current} 不能流转为 {target}")
        order.status = target
        order.updated_at = datetime.now()
        for key, value in (extra or {}).items():
            setattr(order, key, value)
        await db.commit()
        await db.refresh(order)
        logger.info("订单 %s 状态 %s -> %s", order.order_number, current, target)
        return await self.get_order(db, order.id)

    async def mark_paid(
        self, db: AsyncSession, order_id: int, *, transaction_id: Optional[str] = None, scope_user: Any = None
    ) -> Dict[str, Any]:
        """标记已支付（记录支付流水号与时间）"""
        return await self._transition(
            db,
            order_id,
            allowed=("pending",),
            target="paid",
            scope_user=scope_user,
            extra={
                "payment_status": "paid",
                "paid_at": datetime.now(),
                "transaction_id": transaction_id,
            },
        )

    async def mark_shipped(self, db: AsyncSession, order_id: int, *, scope_user: Any = None) -> Dict[str, Any]:
        """标记已发货"""
        return await self._transition(
            db, order_id, allowed=("paid",), target="shipped", scope_user=scope_user,
            extra={"shipped_at": datetime.now()},
        )

    async def mark_delivered(self, db: AsyncSession, order_id: int, *, scope_user: Any = None) -> Dict[str, Any]:
        """标记已收货"""
        return await self._transition(
            db, order_id, allowed=("shipped",), target="delivered", scope_user=scope_user,
            extra={"delivered_at": datetime.now()},
        )

    async def cancel_order(self, db: AsyncSession, order_id: int, *, scope_user: Any = None) -> Dict[str, Any]:
        """取消订单并**回滚库存**（仅未发货订单可取消）"""
        order = await db.get(Order, order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        if str(order.status or "") not in CANCELLABLE:
            raise ConflictError(f"订单当前状态 {order.status} 不可取消（已发货请走退款）")

        items = (
            await db.execute(select(OrderItem).where(OrderItem.order == order.id))
        ).scalars().all()
        now = datetime.now()
        for item in items:
            product = await db.get(Product, int(item.product_id)) if item.product_id else None
            if product is not None:
                product.stock = int(product.stock or 0) + int(item.quantity or 0)
                product.updated_at = now

        return await self._transition(
            db, order_id, allowed=CANCELLABLE, target="cancelled", scope_user=scope_user,
            extra={"updated_at": now},
        )

    async def refund_order(
        self,
        db: AsyncSession,
        order_id: int,
        *,
        restore_stock: bool = False,
        reason: Optional[str] = None,
        scope_user: Any = None,
    ) -> Dict[str, Any]:
        """标记退款（可选同时回滚库存，用于退货退款）"""
        order = await db.get(Order, order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        if str(order.payment_status or "") != "paid":
            raise ConflictError("只有已支付的订单才能退款")

        if restore_stock:
            items = (
                await db.execute(select(OrderItem).where(OrderItem.order == order.id))
            ).scalars().all()
            now = datetime.now()
            for item in items:
                product = await db.get(Product, int(item.product_id)) if item.product_id else None
                if product is not None:
                    product.stock = int(product.stock or 0) + int(item.quantity or 0)
                    product.updated_at = now

        order.notes = (order.notes or "") + (f"\n[退款] {reason}" if reason else "\n[退款]")
        return await self._transition(
            db, order_id, allowed=ORDER_STATUSES, target="refunded", scope_user=scope_user,
            extra={"payment_status": "refunded", "updated_at": datetime.now()},
        )

    async def order_stats(self, db: AsyncSession, *, days: int = 30) -> Dict[str, Any]:
        """订单统计：按状态计数 + 已结算金额（按币种无字段，故只给金额合计）"""
        since = datetime.now() - timedelta(days=days)
        by_status = (
            await db.execute(
                select(Order.status, func.count()).where(Order.created_at >= since).group_by(Order.status)
            )
        ).all()
        settled_amount = (
                             await db.execute(
                                 select(func.sum(Order.total_amount)).where(
                                     Order.created_at >= since, Order.status.in_(SETTLED)
                                 )
                             )
                         ).scalar() or 0
        total_orders = (
                           await db.execute(
                               select(func.count()).select_from(Order).where(Order.created_at >= since)
                           )
                       ).scalar() or 0
        return {
            "period_days": days,
            "total_orders": int(total_orders),
            "by_status": {row[0] or "unknown": int(row[1]) for row in by_status},
            "settled_amount": float(_money(settled_amount)),
        }

    # ------------------------------------------------------------------ 输出
    @staticmethod
    def _product_out(row: Product) -> Dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "price": float(_money(row.price)),
            "original_price": float(_money(row.original_price)) if row.original_price is not None else None,
            "stock": int(row.stock or 0),
            "sku": row.sku,
            "category_id": row.category_id,
            "is_active": bool(row.is_active),
            "is_featured": bool(row.is_featured),
            "description": row.description,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _order_out(row: Order) -> Dict[str, Any]:
        return {
            "id": row.id,
            "order_number": row.order_number,
            "user_id": row.user_id,
            "status": row.status,
            "payment_status": row.payment_status,
            "total_amount": float(_money(row.total_amount)),
            "shipping_amount": float(_money(row.shipping_amount)),
            "discount_amount": float(_money(row.discount_amount)),
            "payment_method": row.payment_method,
            "transaction_id": row.transaction_id,
            "shipping_address": row.shipping_address,
            "notes": row.notes,
            "created_at": row.created_at,
            "paid_at": row.paid_at,
            "shipped_at": row.shipped_at,
            "delivered_at": row.delivered_at,
        }


shop_service = ShopService()
