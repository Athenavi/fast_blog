"""menu 模块：后台菜单与菜单项

路由前缀：``/api/v3/system/menu``

数据模型（``shared/models/menu``）::

    menus(id, name, slug, description, is_active)
      └── menu_items(id, menu_id, parent_id 自引用, title, url, target, order_index, is_active)

说明：``menu_items.parent_id`` 没有外键约束（历史设计），树结构在应用层组装。
前端「菜单驱动动态路由」= 本模块的 ``/tree`` + ``/permission/my`` 的权限码，两者在
Phase 7 由 Vue 后台组合（注意：这与 FastApiAdmin 的 ``sys_menu`` 单表模型不同）。

权限码：``menu:view`` / ``menu:create`` / ``menu:edit`` / ``menu:delete``
"""
