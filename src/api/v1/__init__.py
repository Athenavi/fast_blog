import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.misc import logger


# 延迟导入模块以避免循环导入
def _import_modules():
    """延迟导入模块以避免循环导入"""
    import importlib
    import traceback

    modules = {}
    module_names = [
        "articles",
        "home",
        "responses",
        "users",
        "blog",
        "category_ext",
        "category_management",
        "admin_settings",
        "user_management",
        "user_settings",
        # "relations",
        "media",
        "notifications",
        "misc",
        "comment_config",  # 新增评论配置模块
        "backup",  # 备份管理模块
        "roles",
    ]

    for name in module_names:
        try:
            module = importlib.import_module(f".{name}", package=__name__)
            modules[name] = module
        except ImportError as e:
            print(f"Failed to import module {name}: {e}")
            print(traceback.format_exc())
            modules[name] = None  # 确保即使导入失败也有一个值
        except Exception as e:
            print(f"Error importing module {name}: {e}")
            print(traceback.format_exc())
            modules[name] = None  # 确保即使导入失败也有一个值

    return modules


# 定义模块列表，但延迟导入
__all__ = [
    "articles",
    "dashboard",
    "responses",
    "users",
    "blog",
    "category_ext",
    "category_management",
    "admin_settings",
    "user_settings",
    # "relations",
    "media",
    "notifications",
    "misc",
    "comment_config",
    "roles",
]

api_v1_router = APIRouter(prefix="/api/v1", tags=["api-v1"])


# 延迟包含路由以避免循环导入
def _include_routers():
    """延迟包含路由以避免循环导入"""
    modules = _import_modules()

    # 检查每个模块是否成功导入，只有成功的才添加路由
    if modules.get('articles'):
        api_v1_router.include_router(modules['articles'].router)
    else:
        print("Warning: articles module could not be imported, skipping router inclusion")
    
    if modules.get('users'):
        api_v1_router.include_router(modules['users'].router)
    else:
        print("Warning: users module could not be imported, skipping router inclusion")
        
    # 注册现代化首页API
    try:
        import src.api.v1.home as home_module
        api_v1_router.include_router(home_module.router)
        print("Successfully registered home router")
    except ImportError as e:
        print(f"Failed to import home module: {e}")
        # 回退到旧版home模块
        if modules.get('home'):
            api_v1_router.include_router(modules['home'].router)
            print("Warning: Using legacy home module")
        else:
            print("Warning: home module could not be imported, skipping router inclusion")
        
    if modules.get('blog'):
        api_v1_router.include_router(modules['blog'].router)
    else:
        print("Warning: blog module could not be imported, skipping router inclusion")
        
    if modules.get('category_ext'):
        api_v1_router.include_router(modules['category_ext'].router)
    else:
        print("Warning: category_ext module could not be imported, skipping router inclusion")
        
    if modules.get('category_management'):
        api_v1_router.include_router(modules['category_management'].router)
    else:
        print("Warning: category_management module could not be imported, skipping router inclusion")
        
    if modules.get('admin_settings'):
        api_v1_router.include_router(modules['admin_settings'].router)
    else:
        print("Warning: admin_settings module could not be imported, skipping router inclusion")
        
    if modules.get('user_management'):
        api_v1_router.include_router(modules['user_management'].router)
    else:
        print("Warning: user_management module could not be imported, skipping router inclusion")
        
    if modules.get('user_settings'):
        api_v1_router.include_router(modules['user_settings'].router)
    else:
        print("Warning: user_settings module could not be imported, skipping router inclusion")
        
    if modules.get('media'):
        api_v1_router.include_router(modules['media'].router)
    else:
        print("Warning: media module could not be imported, skipping router inclusion")
        
    if modules.get('notifications'):
        api_v1_router.include_router(modules['notifications'].router)
    else:
        print("Warning: notifications module could not be imported, skipping router inclusion")
        
    if modules.get('misc'):
        api_v1_router.include_router(modules['misc'].router)
    else:
        print("Warning: misc module could not be imported, skipping router inclusion")
        
    if modules.get('comment_config'):
        api_v1_router.include_router(modules['comment_config'].router)
    else:
        print("Warning: comment_config module could not be imported, skipping router inclusion")
        
    if modules.get('backup'):
        api_v1_router.include_router(modules['backup'].router)
    else:
        print("Warning: backup module could not be imported, skipping router inclusion")
        
    if modules.get('roles'):
        api_v1_router.include_router(modules['roles'].router)
    else:
        print("Warning: roles module could not be imported, skipping router inclusion")
        
    # 单独处理 dashboard 模块
    try:
        import src.api.v1.dashboard as dashboard_module
        api_v1_router.include_router(dashboard_module.router)
    except ImportError:
        print("Failed to import dashboard module")
    except Exception as e:
        print(f"Error importing dashboard module: {e}")


_include_routers()
from fastapi import Request, Depends
from src.auth import authenticate_user
from src.utils.security.jwt_handler import get_jwt_strategy
import secrets
import time
from typing import Dict, Optional
from pydantic import BaseModel

refresh_tokens_storage: Dict[str, Dict] = {}


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


@api_v1_router.post("/auth/login",
                    summary="用户登录",
                    description="用户使用邮箱和密码进行登录，成功后返回JWT令牌",
                    response_description="返回认证令牌和用户信息")
async def api_login(login_request: LoginRequest):
    try:
        email = login_request.email
        password = login_request.password
        remember_me = login_request.remember_me

        if not email or not password:
            return JSONResponse({"success": False, "error": "邮箱和密码不能为空"}, status_code=400)

        user = await authenticate_user(email, password)
        if not user:
            return JSONResponse({"success": False, "error": "邮箱或密码错误", "message": "邮箱或密码错误"},
                                status_code=401)

        # 生成JWT token
        strategy = get_jwt_strategy()
        access_token = await strategy.write_token(user)

        # 生成刷新令牌
        refresh_token_expires = 30 * 24 * 60 * 60 if remember_me else 7 * 24 * 60 * 60  # 记住我：30天，否则7天
        refresh_token = secrets.token_urlsafe(32)
        refresh_tokens_storage[refresh_token] = {
            "user_id": user.id,
            "expires_at": time.time() + refresh_token_expires
        }

        # 创建响应对象并设置cookie
        response = JSONResponse(content={
            "success": True,
            "data": {
                "token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_active": user.is_active
                }
            }
        })

        # 根据remember_me参数设置不同的过期时间
        access_token_max_age = 30 * 24 * 60 * 60 if remember_me else 3600  # 记住我：30天，否则1小时
        refresh_token_max_age = 30 * 24 * 60 * 60 if remember_me else 7 * 24 * 60 * 60  # 记住我：30天，否则7天

        # 设置认证cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # 在生产环境中应设为True（如果使用HTTPS）
            samesite="strict",
            max_age=access_token_max_age
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,  # 在生产环境中应设为True（如果使用HTTPS）
            samesite="strict",
            max_age=refresh_token_max_age
        )

        return response
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@api_v1_router.post("/auth/register",
                    summary="用户注册",
                    description="新用户注册账户",
                    response_description="返回创建的用户信息")
async def api_register(register_request: RegisterRequest):
    try:
        username = register_request.username
        email = register_request.email
        password = register_request.password

        if not username or not email or not password:
            return JSONResponse({"success": False, "error": "用户名、邮箱和密码不能为空"}, status_code=400)

        # 导入用户管理器来处理注册
        from src.utils.database.main import get_async_session
        from src.auth.user_manager import UserManager
        from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
        from src.models.user import User as UserModel

        async for session in get_async_session():
            user_db = SQLAlchemyUserDatabase(session, UserModel)
            user_manager = UserManager(user_db)

            try:
                # 创建用户，包含必要的字段
                user_data = {
                    "username": username,
                    "email": email,
                    "is_active": True,
                    "register_ip": "127.0.0.1"  # 由于不再使用request，暂时设为默认值
                }
                
                # 将密码单独处理，不直接传递给模型
                user = await user_manager.create({**user_data, "password": password})

                return JSONResponse({
                    "success": True,
                    "data": {
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "username": user.username,
                            "is_active": user.is_active
                        }
                    }
                })
            except Exception as e:
                # 检查具体错误类型
                if "already exists" in str(e) or "UNIQUE constraint failed" in str(e):
                    if "username" in str(e):
                        return JSONResponse({"success": False, "error": "用户名已存在"}, status_code=409)
                    elif "email" in str(e):
                        return JSONResponse({"success": False, "error": "邮箱已被注册"}, status_code=409)
                    else:
                        return JSONResponse({"success": False, "error": "用户名或邮箱已存在"}, status_code=409)
                else:
                    import traceback
                    print(f"Registration error: {str(e)}")
                    print(traceback.format_exc())
                    return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@api_v1_router.post("/auth/logout",
                    summary="用户登出",
                    description="用户登出，清除认证令牌",
                    response_description="返回登出状态信息")
async def api_logout(request: Request):
    # 从请求中获取刷新令牌并从存储中删除
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token and refresh_token in refresh_tokens_storage:
        del refresh_tokens_storage[refresh_token]

    # 创建响应对象并清除认证cookie
    response = JSONResponse({
        "success": True,
        "message": "已成功注销"
    })

    # 清除认证cookie
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return response


# 添加刷新token的API端点
@api_v1_router.post("/auth/refresh",
                    summary="刷新认证令牌",
                    description="使用刷新令牌获取新的访问令牌",
                    response_description="返回新的认证令牌")
async def api_refresh_token(refresh_request: RefreshTokenRequest, request: Request):
    try:
        refresh_token = refresh_request.refresh_token

        if not refresh_token:
            # 尝试从cookie获取刷新令牌
            refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            return JSONResponse({"success": False, "error": "刷新令牌不能为空"}, status_code=400)

        # 验证刷新令牌
        if refresh_token not in refresh_tokens_storage:
            return JSONResponse({"success": False, "error": "无效的刷新令牌"}, status_code=401)

        token_info = refresh_tokens_storage[refresh_token]
        if token_info["expires_at"] < time.time():
            # 刷新令牌已过期，删除它
            del refresh_tokens_storage[refresh_token]
            return JSONResponse({"success": False, "error": "刷新令牌已过期"}, status_code=401)

        # 获取用户
        from src.utils.database.main import get_async_session
        from src.auth.user_manager import UserManager
        from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
        from src.models.user import User as UserModel

        async for session in get_async_session():
            user_db = SQLAlchemyUserDatabase(session, UserModel)
            user_manager = UserManager(user_db)

            user = await user_manager.get(token_info["user_id"])
            if not user or not user.is_active:
                return JSONResponse({"success": False, "error": "用户不存在或已被禁用"}, status_code=401)

            # 生成新的访问令牌
            strategy = get_jwt_strategy()
            new_access_token = await strategy.write_token(user)

            # 生成新的刷新令牌（可选，也可以保留旧的）
            new_refresh_token = secrets.token_urlsafe(32)
            refresh_tokens_storage[new_refresh_token] = {
                "user_id": user.id,
                "expires_at": time.time() + 7 * 24 * 60 * 60  # 7天后过期
            }

            # 删除旧的刷新令牌
            del refresh_tokens_storage[refresh_token]

            # 创建响应对象并设置新的cookie
            response = JSONResponse(content={
                "success": True,
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "data": {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "is_active": user.is_active
                    }
                }
            })

            # 更新认证cookie
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=False,  # 在生产环境中应设为True（如果使用HTTPS）
                samesite="strict",
                max_age=3600  # 1小时
            )

            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=False,  # 在生产环境中应设为True（如果使用HTTPS）
                samesite="strict",
                max_age=7 * 24 * 60 * 60  # 7天
            )

            return response
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# QR登录相关API
from src.api.v1.user_utils.qrlogin_utils import qr_login, check_qr_login_back, phone_scan_back
from src.extensions import cache
from src.setting import app_config


@api_v1_router.get("/qr/generate",
                   summary="生成二维码",
                   description="为QR登录生成二维码",
                   response_description="返回二维码相关信息")
async def api_generate_qr(request: Request):
    try:
        # 创建一个logger实例
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"QR generation request from: {request.client.host}")
        result = await qr_login(
            request,
            sys_version="1.0",
            global_encoding=app_config.global_encoding,
            domain=app_config.domain,
            cache_instance=cache
        )
        logger.info(
            f"QR generation result: {result.get('success', 'no_success_field') if isinstance(result, dict) else 'non_dict_result'}")
        return result
    except Exception as e:
        from src.logger_config import logger
        import traceback
        logger.error(f"An error occurred: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'message': f'Failed to generate QR code: {str(e)}'
        }


@api_v1_router.get("/qr/status",
                   summary="检查二维码状态",
                   description="检查QR登录二维码的状态",
                   response_description="返回二维码登录状态")
async def api_check_qr_status(request: Request):
    try:
        result = await check_qr_login_back(request, cache)
        return result
    except Exception as e:
        from src.logger_config import logger
        logger.error(f"An error occurred checking QR status: {e}")
        return {
            'success': False,
            'message': 'Failed to check QR code status'
        }


# 添加检查用户名和邮箱的API
from src.models.user import User
from sqlalchemy import func
from src.extensions import get_async_db_session as get_async_db


@api_v1_router.get("/check-username",
                   summary="检查用户名可用性",
                   description="检查指定用户名是否可用",
                   response_description="返回用户名可用性状态")
async def api_check_username(username: str, db: AsyncSession = Depends(get_async_db)):
    try:
        from sqlalchemy import select
        existing_user_query = select(User).where(func.lower(User.username) == func.lower(username))
        existing_user_result = await db.execute(existing_user_query)
        existing_user = existing_user_result.scalar_one_or_none()
        available = existing_user is None
        return JSONResponse({"success": True, "available": available, "exists": not available})
    except Exception as e:
        import traceback
        print(f"Check username error: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@api_v1_router.get("/check-email",
                   summary="检查邮箱可用性",
                   description="检查指定邮箱是否可用",
                   response_description="返回邮箱可用性状态")
async def api_check_email(email: str, db: AsyncSession = Depends(get_async_db)):
    try:
        from sqlalchemy import select
        existing_user_query = select(User).where(func.lower(User.email) == func.lower(email))
        existing_user_result = await db.execute(existing_user_query)
        existing_user = existing_user_result.scalar_one_or_none()
        available = existing_user is None
        return JSONResponse({"success": True, "available": available, "exists": not available})
    except Exception as e:
        import traceback
        print(f"Check email error: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# 添加手机扫码登录API
from src.api.v1.user_utils.qrlogin_utils import phone_scan_back
from src.auth.auth_deps import _get_current_active_user


@api_v1_router.get("/phone/scan",
                   summary="手机扫码登录",
                   description="处理手机扫码登录回调",
                   response_description="返回扫码登录结果")
async def api_phone_scan(request: Request):
    from src.extensions import cache

    # 尝试获取当前用户，如果未登录则返回特殊错误
    try:
        current_user = await _get_current_active_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            # 检查是否是来自移动页面的请求，如果是，返回特殊响应以供前端处理
            user_agent = request.headers.get('user-agent', '').lower()
            is_mobile_request = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])

            if is_mobile_request:
                # 对于移动设备，返回特殊状态，让前端可以处理登录重定向
                return {
                    'success': False,
                    'requires_auth': True,
                    'message': 'User not authenticated. Please log in to continue.',
                    'action': 'redirect_to_login'
                }
            else:
                # 对于非移动设备，返回标准401错误
                return {
                    'success': False,
                    'requires_auth': True,
                    'message': 'User not authenticated. Please log in to your mobile device first.',
                    'action': 'redirect_to_login'
                }
        else:
            # 其他错误，重新抛出
            raise e

    try:
        result = await phone_scan_back(request, current_user=current_user, cache_instance=cache)
        return result
    except Exception as e:
        print(f"An error occurred in phone scan: {e}")
        return {
            'success': False,
            'message': f'Failed to handle phone scan: {str(e)}'
        }


# 添加公共缩略图路由，绕过可能的认证机制
from src.utils.security.safe import is_valid_hash
from src.utils.image.processing import generate_thumbnail, get_file_mime_type
from src.setting import AppConfig

base_dir = AppConfig.base_dir
from fastapi.responses import JSONResponse

from pathlib import Path
from fastapi import Query, HTTPException
from fastapi.responses import FileResponse


@api_v1_router.get("/thumbnail")
async def public_media_thumbnail(
        data: str = Query(...),
):
    """
    获取媒体缩略图
    直接从本地文件系统读取，无需数据库连接
    """
    # 1. 验证哈希参数
    # 移除可能存在的文件扩展名
    clean_data = data
    if '.' in clean_data:
        clean_data = clean_data.split('.')[0]
    
    if not is_valid_hash(64, clean_data):
        raise HTTPException(status_code=400, detail="无效的文件哈希")
    
    # 使用清理后的数据
    data = clean_data
    
    print(f"请求缩略图: {data}")

    # 2. 构建缩略图路径（与主函数一致的结构）
    thumbnail_path = Path(f"storage/thumbnails/{data[:2]}/{data}.jpg")

    # 3. 如果缩略图存在，直接返回
    print(f"检查缩略图路径: {thumbnail_path}")
    if thumbnail_path.exists():
        print(f"找到现有缩略图: {thumbnail_path}")
        return FileResponse(
            thumbnail_path,
            media_type='image/jpeg',
            headers={"Cache-Control": "max-age=2592000"}
        )
    else:
        print(f"缩略图不存在: {thumbnail_path}")

    # 4. 如果缩略图不存在，查找原始文件路径
    original_path = Path(f"storage/objects/{data[:2]}/{data}")

    # 5. 检查原始文件是否存在
    if not original_path.exists():
        # 如果原始文件也不存在，返回404
        raise HTTPException(status_code=404, detail="文件不存在")

    # 6. 确保缩略图目录存在
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"创建缩略图目录: {thumbnail_path.parent}")

    # 7. 生成缩略图（在后台线程中执行）
    print(f"开始生成缩略图: {original_path} -> {thumbnail_path}")
    await generate_thumbnail_async(original_path, thumbnail_path, filehash=data)
    print(f"缩略图生成完成")

    # 8. 返回生成的缩略图
    if thumbnail_path.exists():
        print(f"返回生成的缩略图: {thumbnail_path}")
        return FileResponse(
            thumbnail_path,
            media_type='image/jpeg',
            headers={"Cache-Control": "max-age=2592000"}
        )
    else:
        print(f"缩略图生成失败: {thumbnail_path}")
        raise HTTPException(status_code=500, detail="缩略图生成失败")


async def generate_thumbnail_async(source_path: Path, thumb_path: Path, filehash: str) -> None:
    """
    异步生成缩略图
    """
    import os

    # 先获取文件MIME类型
    try:
        mime_type = await get_file_mime_type(filehash)
    except Exception as e:
        print(f"获取MIME类型失败: {e}")
        mime_type = 'application/octet-stream'

    # 定义一个同步函数来处理缩略图生成
    def sync_generate_thumbnail():
        try:
            # 根据文件类型选择适当的处理方法
            if mime_type.startswith('image/'):
                # 使用图像缩略图生成函数
                generate_thumbnail(str(source_path), str(thumb_path))
            elif mime_type.startswith('video/'):
                # 使用视频缩略图生成函数
                from src.utils.image.processing import create_video_thumbnail
                success = create_video_thumbnail(str(source_path), str(thumb_path))
                if not success:
                    # 如果视频缩略图创建失败，使用默认图标
                    print(f"视频缩略图生成失败，使用默认图标")
                    return False
            else:
                # 不支持的文件类型
                print(f"不支持的文件类型: {mime_type}")
                return False

            return os.path.exists(str(thumb_path))
        except Exception as e:
            print(f"缩略图生成失败: {e}")
            return False

    # 在线程池中执行同步的缩略图生成
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, sync_generate_thumbnail)
