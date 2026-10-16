"""setting 模块：系统配置（key/value）

路由前缀：``/api/v3/system/setting``

数据模型：``system_settings(id, setting_key, setting_value, setting_type, description,
is_public, created_at, updated_at)``（``shared/models/system/system_settings.py``）。

对应 FastApiAdmin 的 ``params``（``sys_param``）模块：语义相同（可配置参数），
因此直接复用 fast_blog 已有的 ``system_settings`` 表，不新建 ``sys_param``。

权限码：``settings:view`` / ``settings:edit``
"""
