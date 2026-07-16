# FastBlog 支付系统

综合性支付解决方案，支持多种支付方式。

## 支持的支付方式

- **传统支付**: Stripe, PayPal, 支付宝, 微信支付
- **加密货币**: BTC, ETH, USDT, USDC
- **x402 微支付**: 微支付场景支持
- **NFT 验证**: NFT 持有者内容解锁
- **税务计算**: VAT/GST 自动计算

## 架构

```
shared/services/payment/
├── __init__.py              # 统一支付服务入口
├── payment_gateway.py       # 传统支付网关
├── crypto_payment.py        # 加密货币支付
├── tax_compliance.py        # 税务和合规性
└── order_management.py      # 订单管理
```

## API 端点

| 端点                                       | 说明        |
|------------------------------------------|-----------|
| `POST /api/v1/payment/create-order`      | 创建订单      |
| `POST /api/v1/payment/pay/{order_id}`    | 处理支付      |
| `POST /api/v1/payment/refund/{order_id}` | 退款        |
| `POST /api/v1/payment/crypto/create`     | 加密货币支付    |
| `POST /api/v1/payment/nft/verify`        | NFT 所有权验证 |
| `POST /api/v1/payment/cart/add`          | 添加到购物车    |
| `POST /api/v1/payment/cart/checkout`     | 结算        |

## 安全

- PCI DSS 合规（通过 tokenization）
- GDPR 合规
- Webhook 签名验证
- 防重放攻击（nonce + timestamp）

> **注意**: 部分支付网关实现为占位模式，需接入对应 API 后启用。
