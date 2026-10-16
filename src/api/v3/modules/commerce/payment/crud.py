"""payment 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.payment import CryptoPayment, PaymentGateway, PaymentTransaction, TaxConfig
from src.api.v3.core.base_crud import CRUDBase


class PaymentGatewayCRUD(CRUDBase[PaymentGateway, dict, dict]):
    model = PaymentGateway
    keyword_fields = ("name", "provider")
    default_order_by = "id"


class PaymentTransactionCRUD(CRUDBase[PaymentTransaction, dict, dict]):
    model = PaymentTransaction
    keyword_fields = ("order_id", "transaction_id")
    #: 交易以时间为序（新在前），与 v2 的 `created_at DESC` 一致
    default_order_by = "created_at"


class CryptoPaymentCRUD(CRUDBase[CryptoPayment, dict, dict]):
    model = CryptoPayment
    keyword_fields = ("wallet_address", "tx_hash", "token_symbol")
    default_order_by = "id"


class TaxConfigCRUD(CRUDBase[TaxConfig, dict, dict]):
    model = TaxConfig
    keyword_fields = ("country", "region", "tax_type")
    default_order_by = "id"


payment_gateway_crud = PaymentGatewayCRUD()
payment_transaction_crud = PaymentTransactionCRUD()
crypto_payment_crud = CryptoPaymentCRUD()
tax_config_crud = TaxConfigCRUD()
