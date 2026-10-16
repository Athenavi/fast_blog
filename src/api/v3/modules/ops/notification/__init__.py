"""notification 模块：站内通知（当前用户视角）

路由前缀：``/api/v3/ops/notification``

数据模型：``notifications(id, recipient→users.id, type, title, message, is_read, read_at,
created_at, updated_at)``。

与 v2 的差异（有意为之）：

  - v2 走 ``src/notification.py`` 的模块函数，那些函数**自己开 session**（``db_manager.get_session()``），
    在请求内会额外占用一条连接；v3 统一用请求的 ``DBSession``，写操作与列表查询在同一事务里。
  - 所有操作都以 **当前登录用户** 为 ``recipient`` 过滤，杜绝"改 id 读别人通知"的越权。

权限：仅需登录（通知是用户私有数据，不使用权限码）。
"""
