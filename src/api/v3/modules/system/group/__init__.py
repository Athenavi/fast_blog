"""group 模块：权限用户组（替代官方的"部门"，承载数据范围）

路由前缀：``/api/v3/system/group``

职责分离（方案 §7.1）：

  - **角色** = 功能权限（菜单级 + 按钮级）
  - **权限组** = 数据范围（能看到/操作谁的数据），支持树形（"本组及以下"）
  - **用户** = 多角色 + 多权限组

数据模型（``config/models.yaml`` 生成）：

  - ``permission_groups``：组本身（树形，``parent_id``）
  - ``user_group_members``：用户 ↔ 组（一人多组）
  - ``role_groups``：角色 ↔ 组（``roles.data_scope=5`` 自定义范围时使用）

权限码：``group:view``（查看）/ ``group:*``（变更）—— 当前映射到 ``settings:*``，
P4 会换成官方的 ``module_system:group:*``（只改 ``core/permission/codes.py`` 与 seed）。
"""
