"""认证依赖项定义 - 避免循环导入"""
from typing import Optional
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User as UserModel
from src.utils.database.main import get_async_session
from src.utils.security.jwt_handler import validate_token_from_request

if TYPE_CHECKING:
    pass


# 通用的认证用户获取函数
async def _get_current_active_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session)  # 使用依赖注入获取异步会话
):
    """内部函数：获取当前活跃用户"""
    from src.utils.security.jwt_handler import validate_token_from_request

    # 从数据库获取用户管理器
    user_db = SQLAlchemyUserDatabase(session, UserModel)
    from src.auth.user_manager import UserManager
    user_manager = UserManager(user_db)

    user = await validate_token_from_request(request, user_manager)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user or invalid token"
        )

    return user
        
    # 如果循环结束仍未返回（理论上不会发生），抛出异常
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate token"
    )


async def _get_current_super_user(request: Request):
    """内部函数：获取当前超级用户"""
    from auth.dependencies import get_current_super_user
    return await get_current_super_user(request)


# 用于检查管理员权限的依赖项（API路由版本 - 返回错误，兼容新版命名）
async def admin_required_api(
        request: Request,
        user: UserModel = Depends(_get_current_super_user)
) -> UserModel:
    """检查用户是否为管理员（超级用户）（API路由版本，兼容新版命名）"""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return user


# 用于检查管理员权限的依赖项（页面路由版本 - 重定向到登录）
async def _get_current_active_user_or_redirect(request: Request):
    """内部函数：获取当前活跃用户，如果未认证则重定向"""
    from src.utils.security.jwt_handler import validate_token_from_request

    # 从数据库获取用户管理器
    async for session in get_async_session():
        user_db = SQLAlchemyUserDatabase(session, UserModel)
        from src.auth.user_manager import UserManager
        user_manager = UserManager(user_db)

        user = await validate_token_from_request(request, user_manager)

        if not user or not user.is_active:
            # 重定向到登录页面，并带上next参数
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)

        return user
        
    # 如果循环结束仍未返回（理论上不会发生），抛出异常
    next_url = str(request.url)
    login_url = f"/login?next={next_url}"
    return RedirectResponse(url=login_url)


async def admin_required_page_dependency(
        request: Request,
        user: 'UserModel' = Depends(_get_current_active_user_or_redirect)
) -> 'UserModel':
    """检查用户是否为管理员（超级用户）（页面路由版本，未登录时重定向到登录页）"""
    # 如果用户是重定向响应，直接返回它
    if isinstance(user, RedirectResponse):
        return user
    if not user.is_superuser:
        # 重定向到登录页面，并带上next参数
        next_url = str(request.url)
        login_url = f"/login?next={next_url}"
        return RedirectResponse(url=login_url)
    return user


# 检查特定权限的装饰器（API路由版本）
def require_permission(permission_code: str):
    """检查用户是否具有特定权限的装饰器（API路由版本）"""

    async def permission_checker(
            request: Request,
            user: 'UserModel' = Depends(_get_current_active_user)
    ) -> 'UserModel':
        if not user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user

    return permission_checker


# 检查特定角色的装饰器（API路由版本）
def require_role(role_name: str):
    """检查用户是否具有特定角色的装饰器（API路由版本）"""

    async def role_checker(
            request: Request,
            user: 'UserModel' = Depends(_get_current_active_user)
    ) -> 'UserModel':
        if not user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions"
            )
        return user

    return role_checker


# 检查特定权限的装饰器（页面路由版本 - 重定向到登录）
def require_permission_page(permission_code: str):
    """检查用户是否具有特定权限的装饰器（页面路由版本，未登录时重定向到登录页）"""

    async def permission_checker(
            request: Request,
            user: 'UserModel' = Depends(_get_current_active_user_or_redirect)
    ) -> 'UserModel':
        # 如果用户是重定向响应，直接返回它
        if isinstance(user, RedirectResponse):
            return user
        if not user.has_permission(permission_code):
            # 重定向到登录页面，并带上next参数
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)
        return user

    return permission_checker


# 检查特定角色的装饰器（页面路由版本 - 重定向到登录）
def require_role_page(role_name: str):
    """检查用户是否具有特定角色的装饰器（页面路由版本，未登录时重定向到登录页）"""

    async def role_checker(
            request: Request,
            user: 'UserModel' = Depends(_get_current_active_user_or_redirect)
    ) -> 'UserModel':
        # 如果用户是重定向响应，直接返回它
        if isinstance(user, RedirectResponse):
            return user
        if not user.has_role(role_name):
            # 重定向到登录页面，并带上next参数
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)
        return user

    return role_checker


# JWT 必需依赖项（API路由版本 - 返回错误）
async def jwt_required_dependency(
        request: Request,
        user: 'UserModel' = Depends(_get_current_active_user)
) -> 'UserModel':
    """JWT 认证依赖项，确保用户已登录（API路由版本）"""
    return user


# JWT 必需依赖项（页面路由版本 - 重定向到登录）
async def jwt_required_page_dependency(
        request: Request,
        user: 'UserModel' = Depends(_get_current_active_user_or_redirect)
) -> 'UserModel':
    """JWT 认证依赖项，确保用户已登录（页面路由版本，未登录时重定向到登录页）"""
    # 如果用户是重定向响应，直接返回它
    if isinstance(user, RedirectResponse):
        return user
    return user


async def authenticate_user(email: str, password: str) -> Optional['UserModel']:
    """验证用户凭据"""
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from src.models.user import User as UserModel
    from src.utils.database.main import get_async_session

    # 导入验证函数，避免循环导入
    from src.api.v1.user_utils import verify_password

    # 获取异步数据库会话 - 正确处理异步生成器
    async for session in get_async_session():
        # 创建用户数据库实例
        user_db = SQLAlchemyUserDatabase(session, UserModel)
        # 创建用户管理器实例
        from src.auth.user_manager import UserManager
        user_manager = UserManager(user_db)

        # 从数据库获取用户
        user = await user_manager.user_db.get_by_email(email)

        if not user:
            return None

        # 验证密码
        if not verify_password(password, user.hashed_password):
            return None

        # 检查用户是否激活
        if not user.is_active:
            return None

        return user
    
    # 如果循环结束仍未返回（理论上不会发生），返回 None
    return None


# 从 cookie 获取 token 的依赖项
async def get_token_from_cookie(request: Request) -> str:
    """从请求 cookie 中获取访问 token"""
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token found in cookies"
        )
    return access_token


# 从 cookie 获取当前活跃用户的依赖项
async def get_current_active_user_from_cookie(
    request: Request,
    session: AsyncSession = Depends(get_async_session)  # 使用依赖注入获取异步会话
):
    """从 cookie 中的 token 获取当前活跃用户"""
    user_db = SQLAlchemyUserDatabase(session, UserModel)
    from src.auth.user_manager import UserManager
    user_manager = UserManager(user_db)

    user = await validate_token_from_request(request, user_manager)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user or invalid token"
        )

    return user


# VIP 用户检查
def require_vip():
    """检查用户是否为VIP用户的装饰器"""

    async def vip_checker(
            request: Request,
            user: 'UserModel' = Depends(_get_current_active_user)
    ) -> 'UserModel':
        if not user.is_vip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="VIP membership required"
            )
        return user

    return vip_checker
