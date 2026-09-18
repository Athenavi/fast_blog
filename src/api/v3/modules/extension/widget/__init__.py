"""widget 模块：页面小部件（区块）

路由前缀：``/api/v3/extension/widget``

数据模型：``widget_instances(id, widget_type, area, title, config, order_index, is_active,
conditions, created_at, updated_at)``。

与 v2 的差异（有意为之）：

  - v2 的 widgets 端点混用「直接 ORM」与「``widget_service`` 内存方法」，其中 3 处
    **漏了 ``await``**（``update_widget_config`` / ``reorder_widgets`` / ``remove_widget``），
    必然 500。v3 只用 ``widget_service`` 的 **DB 方法**（``*_in_db``）与 ORM，消除该缺陷。
  - v2 的 ``POST /register``（``widget_service.register_widget``）是**纯内存、不落库**，
    它是给插件运行时注册 widget 类型用的，不属于 HTTP 管理面，v3 不再暴露；
    类型清单改由 ``widget_service.get_widget_types()`` 只读提供。

权限码：``settings:view``（查看）/ ``settings:edit``（变更）；``/public/**`` 无鉴权。
"""
