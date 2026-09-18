"""permission 模块：权限码（capabilities）查询与权限校验

路由前缀：``/api/v3/system/permission``

权限码的权威定义在 ``scripts/seed_rbac.py``（``resource:action``，写入 ``capabilities.code``）。
本模块只读地暴露它们，并提供"当前用户权限 / 批量校验 / 权限缓存"三类能力。

注意：权限码**不是**可随意新增的资源，新增应由 seed 脚本统一维护，避免代码与 DB 漂移。
"""
