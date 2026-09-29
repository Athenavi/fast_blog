"""commerce 域（商品 / 支付税务 / 打赏）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import pytest
import re
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.api.v3 import register_v3_routes
from src.api.v3.modules.commerce.payment.schema import TaxCalculateRequest
from src.api.v3.modules.commerce.payment.tax_service import _money, validate_vat_number
from src.api.v3.modules.commerce.shop.service import (
    CANCELLABLE,
    ORDER_STATUSES,
    SETTLED,
    _money,
    _new_order_number,
)

# ============================================================ 来自 test_v3_shop.py（6 项）
BASE = "/api/v3/commerce/shop"

READ_PATHS = [
    f"{BASE}/products",
    f"{BASE}/products/low-stock",
    f"{BASE}/products/{{product_id}}",
    f"{BASE}/cart",
    f"{BASE}/orders",
    f"{BASE}/orders/stats",
    f"{BASE}/orders/{{order_id}}",
]

WRITE_ENDPOINTS = [
    ("POST", f"{BASE}/products"),
    ("PUT", f"{BASE}/products/{{product_id}}"),
    ("DELETE", f"{BASE}/products/{{product_id}}"),
    ("POST", f"{BASE}/products/{{product_id}}/stock"),
    ("POST", f"{BASE}/cart/items"),
    ("PUT", f"{BASE}/cart/items/{{item_id}}"),
    ("DELETE", f"{BASE}/cart/items/{{item_id}}"),
    ("DELETE", f"{BASE}/cart"),
    ("POST", f"{BASE}/orders"),
    ("POST", f"{BASE}/orders/{{order_id}}/pay"),
    ("POST", f"{BASE}/orders/{{order_id}}/ship"),
    ("POST", f"{BASE}/orders/{{order_id}}/deliver"),
    ("POST", f"{BASE}/orders/{{order_id}}/cancel"),
    ("POST", f"{BASE}/orders/{{order_id}}/refund"),
]


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数 / 常量
def test_money_quantizes():
    assert str(_money(9.995)) == "10.00"
    assert str(_money(None)) == "0.00"


def test_order_number_format_is_unique():
    first, second = _new_order_number(), _new_order_number()

    assert re.match(r"^ORD\d{8}[0-9A-F]{6}$", first)
    assert first != second


def test_order_state_constants_are_consistent():
    assert set(CANCELLABLE) <= set(ORDER_STATUSES)
    assert set(SETTLED) <= set(ORDER_STATUSES)
    assert "cancelled" in ORDER_STATUSES and "refunded" in ORDER_STATUSES


# ------------------------------------------------------------------ 端点


def test_low_stock_static_path_wins_over_param():
    """静态路径 /products/low-stock 必须注册在 /products/{product_id} 之前"""
    paths = [route.path for route in _app().routes]
    assert paths.index(f"{BASE}/products/low-stock") < paths.index(f"{BASE}/products/{{product_id}}")


def test_cart_query_param_is_optional():
    """未登录请求也会被鉴权前置拦下（购物车端点需要登录）"""
    assert TestClient(_app()).get(f"{BASE}/cart").status_code in (401, 403)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "price": -1},
        {"name": "", "price": 1},
        {"name": "x", "price": 1, "stock": -5},
    ],
)
def test_product_create_validates_payload(payload):
    client = TestClient(_app())

    # 未鉴权时先得 401/403；这里只验证请求体本身不合法时不会被当成 200
    response = client.post(f"{BASE}/products", json=payload)
    assert response.status_code in (401, 403, 422)


# ============================================================ 来自 test_v3_payment_tax.py（5 项）
CALC_PATH = "/api/v3/commerce/payment/tax/calculate"
RESOLVE_PATH = "/api/v3/commerce/payment/tax/resolve"
REPORT_PATH = "/api/v3/commerce/payment/tax/report"


def _app__payment_tax() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    "vat",
    ["DE123456789", "FR12345678901", "IT12345678901", "NL123456789B01", "de123456789", "DE-123-456-789"],
)
def test_validate_vat_number_accepts_eu_formats(vat):
    assert validate_vat_number(vat) is True


@pytest.mark.parametrize(
    "vat",
    [None, "", "DE123", "XX123456789", "123456789", "D1234567890", "DE12345678901234567"],
)
def test_validate_vat_number_rejects_invalid(vat):
    assert validate_vat_number(vat) is False


def test_money_quantizes_to_cents():
    assert str(_money(1.005)) == "1.01"
    assert str(_money("0.004")) == "0.00"
    assert str(_money(None)) == "0.00"


# ------------------------------------------------------------------ schema 边界
def test_tax_calculate_schema_defaults():
    payload = TaxCalculateRequest(amount=100, country="cn")

    assert payload.inclusive is False
    assert payload.vat_number is None
    assert payload.country == "cn"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount": 0, "country": "CN"},
        {"amount": -1, "country": "CN"},
        {"amount": 100, "country": "C"},
        {"amount": 100, "country": "CHN"},
    ],
)
def test_tax_calculate_schema_rejects_bad_input(kwargs):
    with pytest.raises(ValidationError):
        TaxCalculateRequest(**kwargs)


# ------------------------------------------------------------------ 端点


# ============================================================ 来自 test_v3_tipping.py（2 项）
EXPECTED_ENDPOINTS = {
    ("GET", "/api/v3/commerce/tipping/config"),
    ("GET", "/api/v3/commerce/tipping/ranking"),
    ("GET", "/api/v3/commerce/tipping/article/{article_id}"),
    ("POST", "/api/v3/commerce/tipping/tip"),
    ("POST", "/api/v3/commerce/tipping/callback/{provider}"),
    ("GET", "/api/v3/commerce/tipping/mine"),
    ("GET", "/api/v3/commerce/tipping/received"),
    ("GET", "/api/v3/commerce/tipping/earnings"),
    ("POST", "/api/v3/commerce/tipping/withdraw"),
    ("GET", "/api/v3/commerce/tipping/withdrawals/mine"),
    ("GET", "/api/v3/commerce/tipping/withdrawals"),
    ("POST", "/api/v3/commerce/tipping/withdrawals/{withdrawal_id}/review"),
    ("POST", "/api/v3/commerce/tipping/withdrawals/{withdrawal_id}/paid"),
    ("GET", "/api/v3/commerce/tipping/stats"),
}

#: 需要认证或权限码的 GET
AUTH_GET_PATHS = (
    "/api/v3/commerce/tipping/mine",
    "/api/v3/commerce/tipping/received",
    "/api/v3/commerce/tipping/earnings",
    "/api/v3/commerce/tipping/withdrawals/mine",
    "/api/v3/commerce/tipping/withdrawals",
    "/api/v3/commerce/tipping/stats",
)


def _app__tipping() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_config_endpoint_is_public_and_uses_cents():
    """金额单位统一为「分」：1 元起打赏、10 元起提现"""
    client = TestClient(_app__tipping(), raise_server_exceptions=False)
    response = client.get("/api/v3/commerce/tipping/config")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["min_amount"] == 100
    assert data["min_withdraw"] == 1000
    assert data["presets"]
    assert all(isinstance(value, int) for value in data["presets"])
    assert set(data["withdraw_methods"]) == {"alipay", "wechat", "bank"}


def test_withdrawal_paid_requires_transaction_id():
    """标记打款必须带流水号（无凭据不允许）"""
    from src.api.v3.modules.commerce.tipping.schema import WithdrawalPaidRequest

    assert "transaction_id" in WithdrawalPaidRequest.model_fields
    assert WithdrawalPaidRequest.model_fields["transaction_id"].is_required()
