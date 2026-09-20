"""mobile.revenue 模块（T5-11 批次 7）：前台用户端的「我的收益」。

只有 3 个端点，全部**仅需认证**（登记进 ``audit.EXEMPT_WRITE_ENDPOINTS``），
且 ``user_id`` 一律取登录用户，**不接受调用方传入** —— 这是与 v2 最大的差异：
v2 的 revenue 端点完全没有鉴权，`user_id` 由 query 自报，任何人可查/可提现他人收益。
"""
