"""role 模块：角色与角色-权限码绑定

路由前缀：``/api/v3/system/role``

数据模型（``shared/models/rbac``）::

    roles ──(role_capabilities)── capabilities
      └── parent_id 自引用（角色继承，``rbac_service`` 解析时会向上合并）

说明：角色/权限码域**没有**现成的 CRUD service（只有 ``rbac_service`` 的鉴权与分配），
因此本模块自己实现 CRUD，关联表操作与 ``scripts/seed_rbac.py`` 的做法保持一致。

权限码：``user:manage_roles``（角色管理沿用该码，与 ``scripts/seed_rbac.py`` 一致）
"""
