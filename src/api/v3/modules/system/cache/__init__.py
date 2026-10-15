"""cache 模块：v3 系统级缓存管理

**无数据库表**，因此没有 `crud.py` / `model.py`（与 `health` 模块同类）；
读写直接复用共享服务 ``shared/services/core/multi_level_cache.py``。

对应原 astro 后台的「缓存管理」页 —— v2 时代这套能力散在
``src/api/v2/performance/cache_management.py``（多级缓存：stats / warmup / clear /
items 读写 / config）与 ``src/api/v2/admin/cache_management.py``（stats / purge / warmup）。
本模块是二者在 v3 的**能力并集**落地。

权限码：``module_system:cache:view`` / ``:clear`` / ``:warmup`` / ``:write``
（定义在 ``core/permission/codes.py``，由 ``scripts/seed_rbac.py`` 派生进 ``capabilities``）
"""
