"""mobile/user：移动端个人资料与统计

路由前缀：``/api/v3/mobile/user``

迁移说明：legacy 的 ``/api/v3/users/profile`` 手工拼装字段、``PUT`` 时**不校验可改字段**
（任何字段都能写）。v3 改为：

  - ``GET /profile`` 复用 ``AuthService.build_current_user``（带角色与权限码）
  - ``PUT /profile`` 用白名单限定可改字段（昵称类字段不可改用户名/邮箱/权限）
  - ``GET /stats`` 统计当前用户的文章数与评论数

全部需要登录（``CurrentUser``）。
"""
