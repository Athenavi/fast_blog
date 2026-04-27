"""认证模块包初始化"""
# 延迟导入 user_manager，避免循环导入
# from . import user_manager  # 已注释，改为在需要时单独导入

# 导出常用的依赖项
from .auth_deps import (
    admin_required_api,
    admin_required_page,  # 修正：使用正确的函数名
    jwt_required_dependency,
    jwt_required_page_dependency,
    require_permission,
    require_role,
    require_permission_page,
    require_role_page,
    require_vip
)

# 为了兼容性，添加别名
admin_required_page_dependency = admin_required_page
