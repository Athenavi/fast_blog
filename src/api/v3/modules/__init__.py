"""V3 业务模块目录

目录约定（见 ``src/api/v3/core/discover.py``）::

    modules/<domain>/<module>/
        __init__.py
        controller.py   # 顶层 APIRouter 实例，路由前缀 /api/v3/<domain>/<module>
        schema.py       # Pydantic 请求 / 响应模型
        crud.py         # CRUDBase 子类：唯一 DB 访问点
        service.py      # 业务逻辑
        model.py        # 复用 shared.models 的模型（re-export，不重复定义）

新模块建成后必须登记到 ``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES``。
"""
