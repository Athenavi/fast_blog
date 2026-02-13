"""认证模块包初始化"""
from . import user_manager
from .auth_deps import *
# 导出常用的依赖项
from .auth_deps import (
    admin_required_api,
    admin_required_page_dependency,
    jwt_required_dependency,
    jwt_required_page_dependency,
    require_permission,
    require_role,
    require_permission_page,
    require_role_page,
    require_vip
)
