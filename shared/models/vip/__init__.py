"""
vip 子模块 - 模型定义（2026-09-20 批次 16 增补 ``VipPaymentOrder``）

> 前三个模型由代码生成器产出；``VipPaymentOrder`` 是**手写模型**（写法对齐生成器产物），
> 用于记录 VIP 自助开通的支付订单（真钱走 payment-gateway 插件 + 验签回调）。
"""
from .vip_feature import VIPFeature
from .vip_payment_order import VipPaymentOrder
from .vip_plan import VIPPlan
from .vip_subscription import VIPSubscription

__all__ = ['VIPFeature', 'VIPPlan', 'VIPSubscription', 'VipPaymentOrder']
