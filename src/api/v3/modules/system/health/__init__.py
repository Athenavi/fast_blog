"""health 模块：v3 骨架的样板模块（无数据库表，故不含 crud.py / model.py）

用来验证 discover 的自动挂载、fail-fast 与响应格式；同时为部署编排提供
``/api/v3/system/health/live`` 与 ``/api/v3/system/health/ready`` 探针。
"""
