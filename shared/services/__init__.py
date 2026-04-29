"""
共享 API 服务导出模块

该模块导出所有 src/api/v1 中的 API 函数，供 Django Ninja 使用。
这样可以在两个框架之间共享业务逻辑。
"""

# ============================================================================
# 共享服务层 - 提供统一的 SQLAlchemy async 数据访问
# ============================================================================

from .article_manager import (
    get_article_by_id,
    get_articles_by_user_id,
    get_article_count_by_user,
    get_article_with_content,
    get_user_articles_with_pagination,
    create_article,
    update_article,
    update_article_content,
    delete_article,
    increment_article_views,
    search_articles,
)
from .user_manager import (
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    get_user_by_username_or_email,
    update_user_last_login,
    create_user_account,
    update_user_profile,
    check_password_async,
    set_user_password,
    deactivate_user,
    activate_user,
    count_users,
    search_users,
)

# ============================================================================
# API 函数导出 - 供代码生成器生成的路由使用
# 注意：这些是完整的 API 处理函数，包含请求验证、权限检查等逻辑
# ============================================================================
# 防止 IDE 导入优化删除未使用的导入
__all__ = [
    # 用户服务
    'get_user_by_id',
    'get_user_by_username',
    'get_user_by_email',
    'get_user_by_username_or_email',
    'update_user_last_login',
    'create_user_account',
    'update_user_profile',
    'check_password_async',
    'set_user_password',
    'deactivate_user',
    'activate_user',
    'count_users',
    'search_users',
    
    # 文章服务
    'get_article_by_id',
    'get_articles_by_user_id',
    'get_article_count_by_user',
    'get_article_with_content',
    'get_user_articles_with_pagination',
    'create_article',
    'update_article',
    'update_article_content',
    'delete_article',
    'increment_article_views',
    'search_articles',
]


# 初始化日志 - 标记此模块已被加载
def _log_module_loaded():
    """模块加载时的日志记录"""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Shared services module loaded with {len(__all__)} APIs")


# 自动记录模块加载
_log_module_loaded()
