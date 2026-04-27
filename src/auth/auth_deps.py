"""认证依赖项定义 - 基于 Django simplejwt"""
from typing import Optional
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import AccessToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 避免在模块级别导入导致循环导入
# from shared.models.user import User as UserModel
from src.utils.database.main import get_async_session

if TYPE_CHECKING:
    # 仅在类型检查时导入，避免运行时导入
    from shared.models.user import User as UserModel


# 通用的认证用户获取函数
async def _get_current_active_user(
        request: Request,
):
    """内部函数：获取当前活跃用户（基于 Django simplejwt）"""
    # 延迟导入，避免循环导入

    try:
        # 首先尝试从 cookie 获取 token
        # 兼容 FastAPI Request (cookies) 和 Django WSGIRequest (COOKIES)
        if hasattr(request, 'cookies'):
            access_token = request.cookies.get("access_token")
        elif hasattr(request, 'COOKIES'):
            access_token = request.COOKIES.get("access_token")
        else:
            access_token = None

        if not access_token:
            # 如果 cookie 中没有 token，尝试从 Authorization header 获取
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                access_token = authorization[7:]

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 使用 Django simplejwt 验证 token
        try:
            valid_token = AccessToken(access_token)
            user_id = valid_token['user_id']
            # 将 user_id 转换为整数类型，以匹配数据库中的 bigint 类型
            user_id = int(user_id)
        except (TokenError, InvalidToken) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        
        # 检查 token 是否在黑名单中
        from src.utils.token_blacklist import token_blacklist
        if token_blacklist.is_available and token_blacklist.is_blacklisted(access_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 从数据库获取用户
        # 使用 Django ORM 代替 SQLAlchemy，避免 asyncpg 事件循环问题
        from asgiref.sync import sync_to_async
        from apps.user.models import User as DjangoUser

        def get_user_sync():
            try:
                return DjangoUser.objects.get(id=user_id)
            except DjangoUser.DoesNotExist:
                return None

        user = await sync_to_async(get_user_sync)()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def _get_current_super_user(
        request: Request
):
    """内部函数：获取当前超级用户"""
    # 使用本地的_get_current_active_user 函数
    user = await _get_current_active_user(request)
    return user


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
    """内部函数：获取当前活跃用户，如果未认证则重定向（基于 Django simplejwt）"""
    try:
        # 首先尝试从 cookie 获取 token
        # 兼容 FastAPI Request (cookies) 和 Django WSGIRequest (COOKIES)
        if hasattr(request, 'cookies'):
            access_token = request.cookies.get("access_token")
        elif hasattr(request, 'COOKIES'):
            access_token = request.COOKIES.get("access_token")
        else:
            access_token = None

        if not access_token:
            # 如果 cookie 中没有 token，尝试从 Authorization header 获取
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                access_token = authorization[7:]

        if not access_token:
            # 重定向到登录页面
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)

        # 使用 Django simplejwt 验证 token
        try:
            valid_token = AccessToken(access_token)
            user_id = valid_token['user_id']
            # 将 user_id 转换为整数类型，以匹配数据库中的 bigint 类型
            user_id = int(user_id)
        except (TokenError, InvalidToken):
            # Token 无效或过期，重定向到登录页
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)
        except (ValueError, TypeError):
            # user_id 格式错误，重定向到登录页
            next_url = str(request.url)
            login_url = f"/login?next={next_url}"
            return RedirectResponse(url=login_url)

        # 从数据库获取用户
        from src.utils.database.unified_manager import db_manager
        async with db_manager.get_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                next_url = str(request.url)
                login_url = f"/login?next={next_url}"
                return RedirectResponse(url=login_url)

            return user

    except Exception as e:
        print(f"Authentication error: {str(e)}")
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


# JWT 必需依赖项（API 路由版本 - 返回错误）
async def jwt_required_dependency(
        request: Request,
        user: 'UserModel' = Depends(_get_current_active_user)
) -> 'UserModel':
    """JWT 认证依赖项，确保用户已登录（API 路由版本）"""
    return user


# 可选的 JWT 认证依赖项（如果没有 token 则返回 None）
async def jwt_optional_dependency(request: Request) -> Optional['UserModel']:
    """可选的 JWT 认证依赖项，如果认证成功则返回用户，否则返回 None"""
    try:
        user = await _get_current_active_user(request)
        return user
    except HTTPException:
        # 如果认证失败（没有 token 或 token 无效），返回 None
        return None


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
    """验证用户凭据（已废弃，使用 authenticate_user_with_session 代替）"""
    # 延迟导入，避免循环导入
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from shared.models.user import User as UserModel
    from src.utils.database.unified_manager import db_manager

    # 导入验证函数，避免循环导入
    from src.api.v1.user_utils import verify_password

    # 获取异步数据库会话 - 使用上下文管理器确保正确关闭
    async with db_manager.get_session() as session:
        # 创建用户数据库实例
        user_db = SQLAlchemyUserDatabase(session, UserModel)
        # 创建用户管理器实例
        from src.auth.user_manager import UserManager
        user_manager = UserManager(user_db)

        # 从数据库获取用户
        user = await user_manager.user_db.get_by_email(email)

        if not user:
            return None

        # 验证密码（使用 password 字段，兼容 Django）
        if not verify_password(password, user.password):
            return None

        # 检查用户是否激活
        if not user.is_active:
            return None

        return user


async def authenticate_user_with_session(identifier: str, password: str, db: AsyncSession) -> Optional['UserModel']:
    """
    验证用户凭据（使用传入的数据库会话，避免并发冲突）
    
    Args:
        identifier: 用户名或邮箱
        password: 密码
        db: 异步数据库会话（由调用者提供）
        
    Returns:
        用户对象，如果验证失败则返回 None
    """
    from sqlalchemy import select
    from shared.models.user import User as UserModel
    from src.api.v1.user_utils import verify_password
    import re

    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    user = None

    # 判断是邮箱还是用户名，只执行一次查询
    if EMAIL_PATTERN.match(identifier):
        # 通过邮箱查找用户
        result = await db.execute(select(UserModel).where(UserModel.email == identifier))
        user = result.scalar_one_or_none()
    else:
        # 通过用户名查找用户
        result = await db.execute(select(UserModel).where(UserModel.username == identifier))
        user = result.scalar_one_or_none()

    if not user:
        return None

    # 验证密码（使用 password 字段，兼容 Django）
    if not verify_password(password, user.password):
        return None

    # 检查用户是否激活
    if not user.is_active:
        return None

    return user


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
        db: AsyncSession = Depends(get_async_session)
):
    """从 cookie 中的 token 获取当前活跃用户（基于 Django simplejwt）"""
    try:
        # 首先尝试从 cookie 获取 token
        access_token = request.cookies.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token found in cookies",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 使用 Django simplejwt 验证 token
        try:
            valid_token = AccessToken(access_token)
            user_id = valid_token['user_id']
        except (TokenError, InvalidToken) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # 从数据库获取用户
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user or invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


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
