"""V3 core：通用能力层（结构对齐 FastApiAdmin ``app/core``）

为降低启动期耦合、避免循环导入，这里**不做 re-export**（与官方 ``app/core/__init__.py``
保持一致的轻量初始化），按需从具体模块导入::

    from src.api.v3.core.deps import DBSession, CurrentUser, AuthControl, PageDep
    from src.api.v3.core.base_crud import CRUDBase
    from src.api.v3.core.base_schema import SchemaBase
    from src.api.v3.core.exceptions import NotFoundError, register_v3_exception_handlers
    from src.api.v3.core.discover import import_controller, assert_no_route_conflicts
"""
