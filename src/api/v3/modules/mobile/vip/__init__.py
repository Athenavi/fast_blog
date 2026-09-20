"""mobile.vip 模块（2026-09-20 批次 16）：前台 VIP 自助

表：``vip_payment_orders``（本批次新建）。

能力全部**复用** ``shared.services.core.membership.MembershipService``（状态 / 内容访问 /
开通 / 取消），本模块补的是：
  - 订阅与待支付订单的前台视图（``my-subscription``）；
  - **真实支付链路**（``create-payment`` → payment-gateway 插件 → 验签回调 → 开通订阅）；
  - 付费内容列表与"我能不能读这篇"的判定（``premium-content`` / ``check-access``）。

> 顺带修正了订阅状态语义：``MembershipService`` 早期把 ``status == 1`` 当作"有效"
> （v2 遗留），与 ``marketing/vip`` 的 ``0=进行中`` 相反，导致积分兑换 / 管理端手动开通
> 两条路径互相"看不见"。现已统一为 0=进行中 / 1=已过期 / 2=已取消。
"""
