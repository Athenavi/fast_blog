# -*- coding: utf-8 -*-
"""金额相关的服务端校验。

覆盖三件事：
  1. 下单不接受客户端传来的运费/折扣（否则可 0 元下单）；
  2. 支付插件上报的金额与本地订单比对；
  3. 匿名写接口的应用层限流。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.v3.modules.commerce.payment.service import gateway_amount_cents
from src.api.v3.modules.commerce.shop.schema import OrderCreateRequest

pytestmark = pytest.mark.unit


class TestOrderPricing:
    def test_client_supplied_amounts_are_not_accepted(self):
        payload = OrderCreateRequest(
            items=[{"product_id": 1, "quantity": 2}],
            shipping_amount=999,
            discount_amount=999,
        )
        dumped = payload.model_dump(exclude_unset=True)
        assert "discount_amount" not in dumped
        assert "shipping_amount" not in dumped


class TestGatewayAmount:
    def test_cents_are_parsed(self):
        assert gateway_amount_cents({"amount": 1999}) == 1999
        assert gateway_amount_cents({"amount": "1999"}) == 1999

    def test_missing_or_invalid_returns_none(self):
        assert gateway_amount_cents({}) is None
        assert gateway_amount_cents({"amount": None}) is None
        assert gateway_amount_cents({"amount": "abc"}) is None


class TestTipCallbackAmountCheck:
    pytestmark = pytest.mark.asyncio

    async def test_amount_mismatch_does_not_mark_paid(self):
        """验签通过但金额与本单不符（如改价支付）：不得把打赏置为 paid。"""
        from src.api.v3.modules.commerce.tipping.service import tipping_service

        tip = MagicMock()
        tip.amount = 1000  # 10 元
        tip.status = "pending"

        with patch(
            "src.api.v3.modules.commerce.tipping.service.payment_flow_service.handle_callback",
            AsyncMock(return_value={
                "verified": True,
                "order_id": "TIP-1",
                "status": "succeeded",
                "transaction_id": "gw-1",
                "amount": 1,  # 只付了 1 分
            }),
        ), patch(
            "src.api.v3.modules.commerce.tipping.service.tip_crud.get_by",
            AsyncMock(return_value=tip),
        ), patch(
            "src.api.v3.modules.commerce.tipping.service.tip_crud.update",
            AsyncMock(),
        ) as update_mock:
            result = await tipping_service.handle_callback(
                AsyncMock(), provider="alipay", payload={}, headers={}
            )

        assert result.get("amount_mismatch") is True
        update_mock.assert_not_awaited()


class _FakeCache:
    def __init__(self):
        self.store = {}
        self._client = self

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, seconds):
        return True

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value


class TestAnonymousRateLimit:
    pytestmark = pytest.mark.asyncio

    async def test_over_limit_raises_429(self):
        from src.api.v3.core.limits import check_ip_rate_limit

        fake = _FakeCache()
        request = MagicMock()
        with patch("src.extensions.cache", fake), patch(
            "shared.utils.client_ip.get_client_ip", return_value="203.0.113.7"
        ):
            for _ in range(3):
                await check_ip_rate_limit(request, "test.scope", limit=3)
            with pytest.raises(HTTPException) as exc:
                await check_ip_rate_limit(request, "test.scope", limit=3)
        assert exc.value.status_code == 429

    async def test_limiter_failure_fails_open(self):
        """限流器自身故障时放行：埋点断掉不该拖垮业务。"""
        from src.api.v3.core.limits import check_ip_rate_limit

        broken = MagicMock()
        broken._client = None
        broken.get.side_effect = RuntimeError("cache down")
        with patch("src.extensions.cache", broken), patch(
            "shared.utils.client_ip.get_client_ip", return_value="203.0.113.7"
        ):
            await check_ip_rate_limit(MagicMock(), "test.scope", limit=1)

class TestShopSettlement:
    pytestmark = pytest.mark.asyncio

    def _db_with_order(self, order):
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = order
        db.execute = AsyncMock(return_value=result)
        return db

    def _order(self, status="pending", total="100.00"):
        order = MagicMock()
        order.id = 1
        order.status = status
        order.total_amount = total
        order.order_number = "ORD1"
        return order

    async def test_pending_order_is_settled(self):
        from src.api.v3.modules.commerce.shop.service import shop_service

        db = self._db_with_order(self._order())
        with patch.object(shop_service, "_transition", AsyncMock()) as transition:
            ok = await shop_service.settle_paid_order(
                db, order_number="ORD1", paid_cents=10000, transaction_id="gw-1"
            )
        assert ok is True
        transition.assert_awaited_once()

    async def test_amount_mismatch_blocks_settlement(self):
        from src.api.v3.modules.commerce.shop.service import shop_service

        db = self._db_with_order(self._order())
        with patch.object(shop_service, "_transition", AsyncMock()) as transition:
            ok = await shop_service.settle_paid_order(
                db, order_number="ORD1", paid_cents=1  # 只付了 1 分
            )
        assert ok is False
        transition.assert_not_awaited()

    async def test_no_order_or_not_pending_is_noop(self):
        from src.api.v3.modules.commerce.shop.service import shop_service

        with patch.object(shop_service, "_transition", AsyncMock()) as transition:
            assert await shop_service.settle_paid_order(
                self._db_with_order(None), order_number="ORD1", paid_cents=10000
            ) is False
            assert await shop_service.settle_paid_order(
                self._db_with_order(self._order(status="paid")),
                order_number="ORD1",
                paid_cents=10000,
            ) is False
        transition.assert_not_awaited()

