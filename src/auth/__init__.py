"""认证模块包初始化"""
from .auth_deps import (
    create_access_token,
    get_current_user,
    get_current_user_or_redirect,
    admin_required,
    admin_required_page,
    jwt_required,
    jwt_required_page,
    jwt_optional_dependency,
    get_current_active_user,      # 向后兼容
    get_current_super_user,       # 向后兼容
)

from .user_manager import get_user_manager, get_user_db

# 保留旧别名
jwt_required_dependency = jwt_required
jwt_required_page_dependency = jwt_required_page
admin_required_api = admin_required
admin_required_page_dependency = admin_required_page

# 显式声明公共导出（消除 ruff F401 误报，并固定包对外的 API 面）
__all__ = [
    "create_access_token",
    "get_current_user",
    "get_current_user_or_redirect",
    "admin_required",
    "admin_required_page",
    "jwt_required",
    "jwt_required_dependency",
    "jwt_required_page",
    "jwt_required_page_dependency",
    "jwt_optional_dependency",
    "get_current_active_user",
    "get_current_super_user",
    "admin_required_api",
    "admin_required_page_dependency",
    "get_user_manager",
    "get_user_db",
]
