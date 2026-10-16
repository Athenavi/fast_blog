"""system/maintenance：维护模式（配置落 ``system_settings``，拦截由中间件完成）

``src/middleware/maintenance_mode.py`` 读取本模块的配置，命中维护时对非白名单请求返回 503。
"""

from src.api.v3.modules.system.maintenance.service import maintenance_service

__all__ = ["maintenance_service"]
