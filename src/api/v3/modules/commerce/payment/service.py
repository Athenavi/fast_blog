"""payment 模块业务逻辑：网关 / 交易 / 加密货币 / 税务 + 发起支付与回调

业务规则（自 v2 ``payment_management.py`` 平移，行为保持一致）：
  - 网关 ``(name, provider)`` 唯一；删除前若已有交易则拒绝；
  - 网关 ``config_data`` 落库为 JSON 字符串，**出参只给 ``has_config_data``**；
  - 交易 ``order_id`` 唯一；成功态（``succeeded`` / ``completed`` / ``paid``）**只能由回调写入**，
    管理端不可直接改；删除仅限 ``pending`` / ``failed`` / ``cancelled``；
  - 税务配置 ``(country.upper(), tax_type, region)`` 唯一，``region`` 为空时按 NULL 判重。

发起支付与回调（``PaymentFlowService``）**委托给支付插件**
（``plugins/payment-gateway``，slug ``payment-gateway``，能力 ``execute:custom:payment``）：
  - ``initiate``：金额按 **元** 入参，转 **分** 后交给插件（插件契约的 amount 单位是分）；
  - ``handle_callback``：**验签不通过一律不更新交易**（fail-closed）；插件未安装时同样拒绝，
    不做任何"没有验签也放行"的降级。
"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.commerce.payment.crud import (
    crypto_payment_crud,
    payment_gateway_crud,
    payment_transaction_crud,
    tax_config_crud,
)
from src.api.v3.modules.commerce.payment.schema import (
    CryptoPaymentCreate,
    CryptoPaymentOut,
    CryptoPaymentUpdate,
    PaymentGatewayCreate,
    PaymentGatewayOut,
    PaymentGatewayUpdate,
    PaymentInitiateRequest,
    PaymentTransactionCreate,
    PaymentTransactionOut,
    PaymentTransactionUpdate,
    TaxConfigCreate,
    TaxConfigOut,
    TaxConfigUpdate,
)

logger = get_logger("commerce.payment")

#: 具备支付能力的插件 slug（``plugins/payment-gateway``）
PAYMENT_PLUGIN_SLUG = "payment-gateway"

#: 视为「已成功」的交易状态：仅回调可写入，管理端不可改
SUCCESS_STATUSES = ("succeeded", "completed", "paid")

#: 允许直接删除的交易状态（v2 同口径）
DELETABLE_STATUSES = ("pending", "failed", "cancelled")


def _dump_json(value: Optional[dict]) -> Optional[str]:
    return json.dumps(value, ensure_ascii=False) if value else None


def _text(value: Optional[str]) -> Optional[str]:
    """空串归一为 None，避免唯一键把 ``''`` 与 ``NULL`` 当成两种值"""
    return value or None


# ---------------------------------------------------------------- 网关
def _gateway_out(row) -> dict:
    data = PaymentGatewayOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_config_data"] = bool(row.config_data)
    return data


class PaymentGatewayService:
    """支付网关配置"""

    async def list_gateways(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        provider: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await payment_gateway_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"provider": provider, "is_active": is_active},
        )
        return [_gateway_out(r) for r in rows], total

    async def get_gateway(self, db: AsyncSession, gateway_id: int) -> dict:
        row = await payment_gateway_crud.get(db, gateway_id)
        if row is None:
            raise NotFoundError("支付网关不存在")
        return _gateway_out(row)

    async def create_gateway(self, db: AsyncSession, payload: PaymentGatewayCreate) -> dict:
        if await payment_gateway_crud.exists(db, name=payload.name, provider=payload.provider):
            raise ConflictError(f"网关已存在: {payload.name} / {payload.provider}")
        row = await payment_gateway_crud.create(
            db,
            payload.model_dump(exclude={"config_data"})
            | {
                "config_data": _dump_json(payload.config_data),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _gateway_out(row)

    async def update_gateway(
        self, db: AsyncSession, gateway_id: int, payload: PaymentGatewayUpdate
    ) -> dict:
        row = await payment_gateway_crud.get(db, gateway_id)
        if row is None:
            raise NotFoundError("支付网关不存在")
        data = payload.model_dump(exclude_unset=True)
        # config_data 缺省表示"保持原值"（前端只看到 has_config_data 布尔位）
        if "config_data" in data:
            data["config_data"] = _dump_json(data.pop("config_data"))
        name = data.get("name", row.name)
        provider = data.get("provider", row.provider)
        if (name, provider) != (row.name, row.provider):
            if await payment_gateway_crud.exists(db, name=name, provider=provider):
                raise ConflictError(f"网关已存在: {name} / {provider}")
        updated = await payment_gateway_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _gateway_out(updated)

    async def delete_gateway(self, db: AsyncSession, gateway_id: int) -> None:
        row = await payment_gateway_crud.get(db, gateway_id)
        if row is None:
            raise NotFoundError("支付网关不存在")
        used = await payment_transaction_crud.count(db, gateway=gateway_id)
        if used:
            raise ConflictError(f"该网关下已有 {used} 条交易记录，不能删除")
        await payment_gateway_crud.remove(db, row)


# ---------------------------------------------------------------- 交易
def _transaction_out(row) -> dict:
    return PaymentTransactionOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class PaymentTransactionService:
    """支付交易记录"""

    async def list_transactions(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        currency: Optional[str] = None,
        user: Optional[int] = None,
        gateway: Optional[int] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await payment_transaction_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={
                "status": status,
                "payment_method": payment_method,
                "currency": currency,
                "user": user,
                "gateway": gateway,
            },
        )
        return [_transaction_out(r) for r in rows], total

    async def get_transaction(self, db: AsyncSession, transaction_id: int) -> dict:
        row = await payment_transaction_crud.get(db, transaction_id)
        if row is None:
            raise NotFoundError("交易不存在")
        return _transaction_out(row)

    async def create_transaction(
        self, db: AsyncSession, payload: PaymentTransactionCreate
    ) -> dict:
        if payload.gateway is not None:
            if await payment_gateway_crud.get(db, payload.gateway) is None:
                raise NotFoundError("支付网关不存在")
        order_id = _text(payload.order_id)
        if order_id and await payment_transaction_crud.exists(db, order_id=order_id):
            raise ConflictError(f"订单号已存在: {order_id}")
        row = await payment_transaction_crud.create(
            db,
            payload.model_dump(exclude={"extra_metadata"})
            | {
                "order_id": order_id,
                "extra_metadata": _dump_json(payload.extra_metadata),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _transaction_out(row)

    async def update_transaction(
        self, db: AsyncSession, transaction_id: int, payload: PaymentTransactionUpdate
    ) -> dict:
        row = await payment_transaction_crud.get(db, transaction_id)
        if row is None:
            raise NotFoundError("交易不存在")
        if row.status in SUCCESS_STATUSES:
            raise BadRequestError("已成功的交易不可修改（状态只能由支付回调写入）")
        data = payload.model_dump(exclude_unset=True)
        if "extra_metadata" in data:
            data["extra_metadata"] = _dump_json(data.pop("extra_metadata"))
        if "order_id" in data:
            data["order_id"] = _text(data["order_id"])
        if data.get("order_id") and data["order_id"] != row.order_id:
            if await payment_transaction_crud.exists(db, order_id=data["order_id"]):
                raise ConflictError(f"订单号已存在: {data['order_id']}")
        if "gateway" in data and data["gateway"] is not None:
            if await payment_gateway_crud.get(db, data["gateway"]) is None:
                raise NotFoundError("支付网关不存在")
        updated = await payment_transaction_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _transaction_out(updated)

    async def delete_transaction(self, db: AsyncSession, transaction_id: int) -> None:
        row = await payment_transaction_crud.get(db, transaction_id)
        if row is None:
            raise NotFoundError("交易不存在")
        if row.status not in DELETABLE_STATUSES:
            raise BadRequestError(
                f"状态为 {row.status} 的交易不可删除，请先置为 cancelled / failed"
            )
        await payment_transaction_crud.remove(db, row)


# ---------------------------------------------------------------- 加密货币支付
def _crypto_out(row) -> dict:
    return CryptoPaymentOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class CryptoPaymentService:
    """加密货币支付"""

    async def list_crypto(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        blockchain: Optional[str] = None,
        status: Optional[str] = None,
        transaction: Optional[int] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await crypto_payment_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"blockchain": blockchain, "status": status, "transaction": transaction},
        )
        return [_crypto_out(r) for r in rows], total

    async def create_crypto(self, db: AsyncSession, payload: CryptoPaymentCreate) -> dict:
        if await payment_transaction_crud.get(db, payload.transaction) is None:
            raise NotFoundError("关联的交易不存在")
        if payload.tx_hash and await crypto_payment_crud.exists(db, tx_hash=payload.tx_hash):
            raise ConflictError(f"交易哈希已存在: {payload.tx_hash}")
        row = await crypto_payment_crud.create(
            db,
            payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()},
        )
        return _crypto_out(row)

    async def update_crypto(
        self, db: AsyncSession, crypto_id: int, payload: CryptoPaymentUpdate
    ) -> dict:
        row = await crypto_payment_crud.get(db, crypto_id)
        if row is None:
            raise NotFoundError("加密支付记录不存在")
        data = payload.model_dump(exclude_unset=True)
        if data.get("tx_hash") and data["tx_hash"] != row.tx_hash:
            if await crypto_payment_crud.exists(db, tx_hash=data["tx_hash"]):
                raise ConflictError(f"交易哈希已存在: {data['tx_hash']}")
        updated = await crypto_payment_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _crypto_out(updated)

    async def delete_crypto(self, db: AsyncSession, crypto_id: int) -> None:
        row = await crypto_payment_crud.get(db, crypto_id)
        if row is None:
            raise NotFoundError("加密支付记录不存在")
        await crypto_payment_crud.remove(db, row)


# ---------------------------------------------------------------- 税务配置
def _tax_out(row) -> dict:
    return TaxConfigOut.model_validate(row, from_attributes=True).model_dump(mode="json")


class TaxConfigService:
    """税务配置"""

    async def list_tax_configs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        tax_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await tax_config_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={
                "country": country.upper() if country else None,
                "region": region,
                "tax_type": tax_type,
                "is_active": is_active,
            },
        )
        return [_tax_out(r) for r in rows], total

    async def _assert_unique(
        self, db: AsyncSession, *, country: str, tax_type: str, region: Optional[str], exclude_id: Optional[int] = None
    ) -> None:
        """(country, tax_type, region) 唯一；region 为空时按 NULL 判重"""
        rows, _total = await tax_config_crud.list(
            db,
            page=1,
            page_size=0,
            filters={"country": country, "tax_type": tax_type},
        )
        for row in rows:
            if exclude_id is not None and row.id == exclude_id:
                continue
            if (row.region or None) == (region or None):
                raise ConflictError(f"税务配置已存在: {country} / {tax_type} / {region or '(ALL)'}")

    async def create_tax_config(self, db: AsyncSession, payload: TaxConfigCreate) -> dict:
        country = payload.country.upper()
        await self._assert_unique(
            db, country=country, tax_type=payload.tax_type, region=payload.region
        )
        row = await tax_config_crud.create(
            db,
            payload.model_dump(exclude={"country", "effective_from"})
            | {
                "country": country,
                "effective_from": payload.effective_from or datetime.now(),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _tax_out(row)

    async def update_tax_config(
        self, db: AsyncSession, config_id: int, payload: TaxConfigUpdate
    ) -> dict:
        row = await tax_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("税务配置不存在")
        data = payload.model_dump(exclude_unset=True)
        if "country" in data and data["country"]:
            data["country"] = data["country"].upper()
        country = data.get("country", row.country)
        tax_type = data.get("tax_type", row.tax_type)
        region = data.get("region", row.region)
        if (country, tax_type, region or None) != (row.country, row.tax_type, row.region or None):
            await self._assert_unique(
                db, country=country, tax_type=tax_type, region=region, exclude_id=row.id
            )
        updated = await tax_config_crud.update(db, row, data | {"updated_at": datetime.now()})
        return _tax_out(updated)

    async def delete_tax_config(self, db: AsyncSession, config_id: int) -> None:
        row = await tax_config_crud.get(db, config_id)
        if row is None:
            raise NotFoundError("税务配置不存在")
        await tax_config_crud.remove(db, row)


# ---------------------------------------------------------------- 发起支付 / 回调
class PaymentFlowService:
    """支付流程：委托支付插件发起支付、处理网关回调

    插件未安装 / 未激活 / 缺能力 / 方法不存在时一律**拒绝**（抛 ``BadRequestError``），
    不做任何本地降级 —— 否则等于把"没有验签"当成成功路径。
    """

    @staticmethod
    async def _plugin_action(action: str, params: dict) -> Any:
        # 延迟导入：避免 commerce 域在导入期就拉起插件管理器
        from src.api.v3.modules.extension.plugin.service import plugin_ops_service

        try:
            return await plugin_ops_service.execute_action(PAYMENT_PLUGIN_SLUG, action, params)
        except NotFoundError as exc:
            raise BadRequestError(
                f"支付插件未安装或未加载（需要 plugins/{PAYMENT_PLUGIN_SLUG}）"
            ) from exc
        except BadRequestError as exc:
            raise BadRequestError(f"支付插件不可用：{exc}") from exc

    async def initiate(self, db: AsyncSession, payload: PaymentInitiateRequest, user_id: int) -> dict:
        """发起支付：金额按 **元** 入参，转 **分** 交给插件"""
        if payload.gateway is not None:
            gateway = await payment_gateway_crud.get(db, payload.gateway)
            if gateway is None:
                raise NotFoundError("支付网关不存在")
            if not gateway.is_active:
                raise BadRequestError("该支付网关未激活")
        result = await self._plugin_action(
            "create_payment",
            {
                "order_id": payload.order_id,
                "amount": int(round(payload.amount * 100)),
                "subject": payload.subject,
                "user_id": user_id,
                "return_url": payload.return_url,
                "cancel_url": payload.cancel_url,
                "notify_url": payload.notify_url,
            },
        )
        if not isinstance(result, dict):
            return {"success": False, "error": "支付插件返回了非预期结果"}
        return result

    async def handle_callback(
        self,
        db: AsyncSession,
        *,
        provider: str,
        payload: dict,
        headers: Optional[dict] = None,
    ) -> dict:
        """处理网关回调：**验签通过才更新交易**，否则原样返回 ``verified=False``"""
        result = await self._plugin_action(
            "verify_callback",
            {"provider": provider, "payload": payload, "headers": headers or {}},
        )
        if not isinstance(result, dict) or not result.get("verified"):
            detail = result.get("error") if isinstance(result, dict) else None
            logger.warning("支付回调验签未通过: provider=%s detail=%s", provider, detail)
            return {"verified": False, "provider": provider}

        order_id = result.get("order_id")
        status = result.get("status") or "succeeded"
        transaction_id = result.get("transaction_id")
        row = (
            await payment_transaction_crud.get_by(db, order_id=order_id) if order_id else None
        )
        if row is None:
            logger.warning("支付回调找不到对应订单: provider=%s order_id=%s", provider, order_id)
            return {"verified": True, "provider": provider, "order_id": order_id, "updated": False}
        data: dict = {"status": status, "updated_at": datetime.now()}
        if transaction_id:
            data["transaction_id"] = transaction_id
        await payment_transaction_crud.update(db, row, data)
        return {
            "verified": True,
            "provider": provider,
            "order_id": order_id,
            "status": status,
            "updated": True,
        }


payment_gateway_service = PaymentGatewayService()
payment_transaction_service = PaymentTransactionService()
crypto_payment_service = CryptoPaymentService()
tax_config_service = TaxConfigService()
payment_flow_service = PaymentFlowService()
