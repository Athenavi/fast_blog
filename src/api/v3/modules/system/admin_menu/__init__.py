"""admin_menu 模块：后台菜单（授权载体）

对应"混合"决策：**后端管授权、前端管结构**。

  - 本模块的 `admin_menus` 只存"稳定标识 + 显示名 + 层级 + 关联权限码"，**不存组件路径**
  - `admin_menus.code` 与前端 `routes.ts` 的 `meta.menuCode`（取路由 `name`）一一对应
  - 前端据此决定"菜单长什么样"，后端据此决定"有哪些菜单是被授权的"
  - 角色 ↔ 菜单授权存 `role_admin_menus`；**权限组不参与菜单授权**（权限组只管数据范围）

路由前缀：``/api/v3/system/admin-menu``

⚠️ 与既有 ``modules/system/menu`` 区分：后者管理**前台导航菜单**（表 `menus`/`menu_items`）。
"""
