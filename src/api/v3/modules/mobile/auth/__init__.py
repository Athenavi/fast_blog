"""mobile/auth：移动端登录与注册

路由前缀：``/api/v3/mobile/auth``

迁移说明（v3 内部迁移，非照搬）：legacy 的 ``/api/v3/auth/login`` 直接用
``auth_legacy.create_jwt_token`` 裸签发 token，**没有**限流、账户锁定、会话轮换与审计。
v3 改为复用 ``modules/system/auth`` 的 ``AuthService``，因此移动端登录自动获得：

  - IP 限流与账户锁定检查
  - 登录尝试记录、审计日志、``user.login`` 事件
  - 2FA 分支（返回 ``requires_2fa`` + 临时 token）
  - 会话轮换（撤销该用户其它会话）

响应统一为 v3 的 ``{code, msg, data, pagination}``。
"""
