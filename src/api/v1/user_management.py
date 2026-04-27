"""
用户管理 API - 处理用户相关的管理功能
精简优化版本
"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, HTTPException, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 导入 SQLAlchemy 模型和服务
from shared.models.user import User as UserModel
from shared.services import create_user_account
# 注意：避免在此处直接导入 article_service，防止循环依赖
# article_service 的导入已移至使用位置
from src.api.v1.responses import ApiResponse
from src.api.v1.user_settings import change_profiles_back
from src.api.v1.user_utils.password_utils import update_password, validate_password_async
from src.auth.auth_deps import _get_current_active_user, jwt_optional_dependency, jwt_required_dependency
from src.extensions import get_async_db_session as get_async_db
from src.setting import app_config
from src.utils.security.ip_utils import get_client_ip

router = APIRouter(prefix="/management", tags=["user-management"])


# ==================== 认证相关 API ====================

@router.post("/auth/login", summary="用户登录（兼容 Django 认证方式）")
async def login_api(
        request: Request,
        username: str = Form(..., description="用户名或邮箱"),
        password: str = Form(..., description="密码"),
        remember_me: bool = Form(False, description="记住我"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    用户登录 API - 与 Django 使用相同的认证方式
    
    支持使用用户名或邮箱进行登录，返回 JWT Token
    """
    try:
        # 尝试通过用户名或邮箱查找用户
        from src.auth.auth_deps import authenticate_user_with_session

        # 先尝试作为邮箱验证，然后作为用户名验证
        # authenticate_user_with_session 会处理两种情况
        user = await authenticate_user_with_session(username, password, db)

        if not user:
            return ApiResponse(success=False, error="用户名或密码错误")

        if not user.is_active:
            return ApiResponse(success=False, error="账户已被禁用")

        # 使用 Django 的 rest_framework_simplejwt 生成 JWT token
        from rest_framework_simplejwt.tokens import RefreshToken

        # 为用户创建 refresh token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # 更新最后登录时间
        from datetime import timezone
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        return ApiResponse(
            success=True,
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "profile_picture": user.profile_picture or None,
                    "is_active": getattr(user, 'is_active', True),
                    "is_superuser": getattr(user, 'is_superuser', False),
                    "is_staff": getattr(user, 'is_staff', False),
                    "vip_level": getattr(user, 'vip_level', 0)
                },
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in login_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/auth/register", summary="用户注册")
async def register_api(
        request: Request,
        username: str = Form(..., description="用户名"),
        email: str = Form(..., description="邮箱"),
        password: str = Form(..., description="密码"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    用户注册 API - 使用 Django 的注册用户方式
    
    - **username**: 用户名（至少 3 个字符）
    - **email**: 邮箱地址（必须符合邮箱格式）
    - **password**: 密码（至少 8 个字符，包含大小写字母和数字）
    """
    try:
        # 验证用户名
        if len(username) < 3:
            return ApiResponse(success=False, error="用户名至少需要 3 个字符")

        # 验证邮箱格式
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return ApiResponse(success=False, error="邮箱格式不正确")

        # 验证密码强度
        if len(password) < 8:
            return ApiResponse(success=False, error="密码至少需要 8 个字符")
        if not re.search(r'[A-Z]', password):
            return ApiResponse(success=False, error="密码必须包含大写字母")
        if not re.search(r'[a-z]', password):
            return ApiResponse(success=False, error="密码必须包含小写字母")
        if not re.search(r'\d', password):
            return ApiResponse(success=False, error="密码必须包含数字")

        # 检查用户名是否已存在
        result = await db.execute(select(UserModel).where(UserModel.username == username))
        if result.scalar_one_or_none():
            return ApiResponse(success=False, error="用户名已存在")

        # 检查邮箱是否已存在
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        if result.scalar_one_or_none():
            return ApiResponse(success=False, error="邮箱已被注册")

        # 使用统一的 SQLAlchemy async 服务层创建用户
        user = await create_user_account(
            db=db,
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        # 使用 Django 的 rest_framework_simplejwt 生成 token
        from rest_framework_simplejwt.tokens import RefreshToken

        # 为生成的用户创建 refresh token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return ApiResponse(
            success=True,
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": getattr(user, 'is_active', True),
                    "is_superuser": getattr(user, 'is_superuser', False),
                    "is_staff": getattr(user, 'is_staff', False),
                    "vip_level": getattr(user, 'vip_level', 0)
                },
                "access_token": access_token,
                "refresh_token": refresh_token
            },
            message="注册成功"
        )
    except ValueError as e:
        # 业务异常返回具体错误信息
        import logging
        logging.warning(f"Business error in register_api: {str(e)}")
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        # 系统异常记录详细日志但返回通用错误消息
        import logging
        import traceback
        logging.error(f"System error in register_api: {str(e)}")
        logging.error(traceback.format_exc())
        return ApiResponse(success=False, error="注册失败，请稍后重试")


@router.post("/auth/logout", summary="用户登出")
async def logout_api(request: Request):
    """
    用户登出 API

    客户端清除 token 即可实现登出
    服务端会将当前 token 加入黑名单（如果 Redis 可用）
    """
    try:
        import json
        from datetime import datetime

        # 尝试从请求中获取 token
        body = await request.body()
        data = json.loads(body) if body else {}
        access_token = data.get('access_token')
        refresh_token_str = data.get('refresh_token')

        # 将 token 加入黑名单
        from src.utils.token_blacklist import token_blacklist

        if access_token:
            # 解析 token 获取过期时间
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from asgiref.sync import sync_to_async

                def parse_token(token_str: str):
                    token = AccessToken(token_str)
                    return token.payload.get('exp')

                exp_timestamp = await sync_to_async(parse_token)(access_token)
                if exp_timestamp:
                    expires_at = datetime.fromtimestamp(exp_timestamp)
                    token_blacklist.add_to_blacklist(access_token, expires_at)
            except Exception as e:
                import logging
                logging.debug(f"无法将 access token 加入黑名单：{e}")

        if refresh_token_str:
            # 将 refresh token 也加入黑名单
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                from asgiref.sync import sync_to_async

                def parse_refresh_token(token_str: str):
                    token = RefreshToken(token_str)
                    return token.payload.get('exp')

                exp_timestamp = await sync_to_async(parse_refresh_token)(refresh_token_str)
                if exp_timestamp:
                    expires_at = datetime.fromtimestamp(exp_timestamp)
                    token_blacklist.add_to_blacklist(refresh_token_str, expires_at)
            except Exception as e:
                import logging
                logging.debug(f"无法将 refresh token 加入黑名单：{e}")

        return ApiResponse(success=True, message="登出成功")
    except Exception as e:
        import logging
        logging.error(f"Error in logout_api: {str(e)}")
        return ApiResponse(success=False, error="登出失败，请稍后重试")


@router.post("/auth/token/refresh", summary="刷新访问令牌")
async def refresh_token_api(request: Request):
    """
    刷新访问令牌 API

    使用 refresh_token 获取新的 access_token

    请求体:
    - **refresh**: refresh_token 字符串
    """
    try:
        import json
        # 解析请求体
        body = await request.body()
        data = json.loads(body)
        refresh_token_str = data.get('refresh')

        if not refresh_token_str:
            return ApiResponse(success=False, error="缺少 refresh token")

        # 使用 Django 的 simplejwt 验证并刷新 token
        from rest_framework_simplejwt.tokens import RefreshToken
        from asgiref.sync import sync_to_async

        def verify_and_refresh_token(token_str: str):
            try:
                refresh = RefreshToken(token_str)
                # 获取新的 access token
                new_access_token = str(refresh.access_token)
                # 可以选择轮换 refresh token（从配置中读取）
                from rest_framework_simplejwt.settings import api_settings
                new_refresh_token = str(refresh) if api_settings.ROTATE_REFRESH_TOKENS else token_str
                return new_access_token, new_refresh_token
            except Exception as e:
                raise ValueError(f"Invalid or expired refresh token: {str(e)}")

        # 同步执行 token 刷新
        new_access_token, new_refresh_token = await sync_to_async(verify_and_refresh_token)(refresh_token_str)

        return ApiResponse(
            success=True,
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            },
            message="Token refreshed successfully"
        )
    except ValueError as e:
        # Token 无效或过期
        import logging
        logging.warning(f"Invalid token in refresh_token_api: {str(e)}")
        return ApiResponse(success=False, error=str(e))
    except Exception as e:
        # 系统异常记录详细日志但返回通用错误消息
        import logging
        import traceback
        logging.error(f"System error in refresh_token_api: {str(e)}")
        logging.error(traceback.format_exc())
        return ApiResponse(success=False, error="Token 刷新失败，请稍后重试")


# ==================== 用户资料相关 API ====================


def _create_article_response(article):
    """创建文章响应数据的辅助函数"""
    # 处理日期时间字段：可能是 datetime 对象或字符串
    created_at = article.created_at.isoformat() if hasattr(article.created_at, 'isoformat') else article.created_at
    updated_at = article.updated_at.isoformat() if hasattr(article.updated_at, 'isoformat') else article.updated_at

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": article.excerpt,
        "cover_image": article.cover_image,
        "tags": [],  # Article 模型没有 tags 字段，使用 tags_list
        "views": article.views or 0,
        "likes": article.likes or 0,
        "created_at": created_at,
        "updated_at": updated_at
    }


def _create_user_response(user):
    """创建用户响应数据的辅助函数（兼容 Django User 模型）"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio or '',
        "location": user.locale or '',
        "website": '',
        "profile_private": user.profile_private,
        "display_name": user.username,
        "locale": user.locale or 'zh_CN',
        "created_at": user.date_joined if hasattr(user, 'date_joined') and user.date_joined else None,
        "updated_at": None,  # Django User 模型没有 updated_at 字段
        "is_active": getattr(user, 'is_active', True),
        "is_superuser": getattr(user, 'is_superuser', False),
        "is_staff": getattr(user, 'is_staff', False),
        "vip_level": getattr(user, 'vip_level', 0),
        "avatar": user.profile_picture or ''
    }


async def _get_user_articles(user_id: int, db: AsyncSession, limit: int = 10):
    """获取用户文章 - 使用 SQLAlchemy async"""
    # 延迟导入以避免循环依赖
    from shared.services.article_manager import get_articles_by_user_id
    return await get_articles_by_user_id(db, user_id, limit)


async def _get_articles_count(user_id: int, db: AsyncSession):
    """获取用户文章数量 - 使用 SQLAlchemy async"""
    # 延迟导入以避免循环依赖
    from shared.services.article_manager import get_article_count_by_user
    return await get_article_count_by_user(db, user_id)


def _get_user_stats(articles_count: int = 0):
    """获取用户统计数据"""
    return {
        'articles_count': articles_count,
        'followers_count': 0,
        'following_count': 0
    }


async def _check_profile_privacy(target_user, current_user_id=None):
    """检查用户资料隐私"""
    if target_user.profile_private and current_user_id != target_user.id:
        return False
    return True


@router.get("/me/profile", response_model=None)
async def get_my_profile_api(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(_get_current_active_user)
):
    """获取我的资料 API"""
    try:
        # 直接调用内部逻辑（已认证的用户）
        return await _get_my_profile_logic(current_user, db)
    except Exception as e:
        import traceback
        print(f"Error in get_my_profile_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"获取资料失败：{str(e)}")


async def _get_my_profile_logic(current_user, db: AsyncSession) -> ApiResponse:
    """获取我的资料的实际逻辑（需要传入已认证的用户）"""

    # 直接从 current_user 获取头像 URL（避免使用 SQLAlchemy 查询）
    avatar_url = None
    if current_user.profile_picture:
        # 查找实际存在的文件（可能是任何支持的图像格式）
        from pathlib import Path
        avatar_dir = Path('static/avatar')
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            avatar_file = avatar_dir / f"{current_user.profile_picture}{ext}"
            if avatar_file.exists():
                avatar_url = f"{app_config.domain}static/avatar/{current_user.profile_picture}{ext}"
                break
        # 如果没有找到对应的文件，使用.webp 作为默认扩展名
        if not avatar_url:
            avatar_url = f"{app_config.domain}static/avatar/{current_user.profile_picture}.webp"

    # 获取用户文章和统计 - 使用 SQLAlchemy async
    # 延迟导入以避免循环依赖
    from shared.services.article_manager import get_articles_by_user_id, get_article_count_by_user

    # 串行执行两个查询（避免并发操作同一会话）
    user_articles = await get_articles_by_user_id(db, current_user.id, 10)
    articles_count = await get_article_count_by_user(db, current_user.id)

    profile_data = {
        "user": _create_user_response(current_user),
        "recent_articles": [_create_article_response(article) for article in user_articles],
        "stats": _get_user_stats(articles_count),
        "is_following": False,
        "has_unread_message": False
    }

    return ApiResponse(success=True, data=profile_data)


@router.get("/{user_id}/profile")
async def get_user_profile_api(
        request: Request,
        user_id: int,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100之间"),
        db: AsyncSession = Depends(get_async_db)
):
    """获取用户公共资料API"""
    try:
        # 获取目标用户信息
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        target_user = result.scalar_one_or_none()

        if not target_user:
            return ApiResponse(success=False, error="用户未找到")

        # 获取当前用户 ID（手动调用，避免依赖注入并发问题）
        current_user_id = None
        try:
            current_user = await jwt_optional_dependency(request)
            if current_user:
                current_user_id = current_user.id
        except Exception:
            pass

        # 检查隐私设置
        if not await _check_profile_privacy(target_user, current_user_id):
            return ApiResponse(success=False, error="此用户资料是私有的")

        # 获取用户数据
        user_articles = []
        articles_count = 0

        if not target_user.profile_private:
            # 使用分页获取文章
            from shared.services.article_manager import get_user_articles_with_pagination
            articles_list, total_count = await get_user_articles_with_pagination(
                db=db,
                user_id=user_id,
                page=page,
                per_page=per_page,
                status=1  # 只获取已发布的文章
            )
            user_articles = articles_list
            articles_count = total_count

        is_following = False
        if current_user_id and current_user_id != user_id:
            # 这里可以添加关注检查逻辑
            pass

        # 计算分页信息
        total_pages = (articles_count + per_page - 1) // per_page if articles_count > 0 else 0

        return ApiResponse(
            success=True,
            data={
                "user": _create_user_response(target_user),
                "recent_articles": [_create_article_response(article) for article in user_articles],
                "stats": _get_user_stats(articles_count),
                "is_following": is_following,
                "has_unread_message": False,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total": articles_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_user_profile_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"获取用户资料失败: {str(e)}")


@router.put("/me/profile", response_model=None)
async def update_my_profile_api(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(jwt_required_dependency)
):
    """更新我的资料 API"""
    try:
        # 直接调用内部逻辑（已认证的用户）
        return await _update_my_profile_logic(request, current_user, db)
    except Exception as e:
        import traceback
        print(f"Error in update_my_profile_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"更新资料失败：{str(e)}")


async def _update_my_profile_logic(request: Request, current_user, db: AsyncSession) -> ApiResponse:
    """更新我的资料的实际逻辑（需要传入已认证的用户）"""

    try:
        form_data = await request.form()

        # 使用服务层更新用户资料
        from shared.services.user_manager import update_user_profile

        updated_user = await update_user_profile(
            db=db,
            user_id=current_user.id,
            username=form_data.get('username', current_user.username),
            bio=form_data.get('bio', current_user.bio or ''),
            locale=form_data.get('locale', current_user.locale or 'zh_CN'),
            profile_private=form_data.get('profile_private') is not None
        )

        if not updated_user:
            return ApiResponse(success=False, error="用户不存在")

        return ApiResponse(
            success=True,
            data={
                "message": "资料更新成功",
                "user": _create_user_response(updated_user)
            }
        )
    except Exception as e:
        await db.rollback()
        raise


@router.get("/me/security/confirm-password")
async def confirm_password_form_api(current_user: UserModel = Depends(jwt_required_dependency)):
    """密码确认表单API"""
    return ApiResponse(
        success=True,
        data={
            "form_type": 'confirm',
            "user_id": current_user.id
        }
    )


@router.post("/me/security/confirm-password")
async def confirm_password_api(
        request: Request,
        current_user: UserModel = Depends(jwt_required_dependency),
        db: AsyncSession = Depends(get_async_db)
):
    """密码确认API"""
    try:
        from utils.security.forms import ConfirmPasswordForm

        form_data = await request.form()
        form = ConfirmPasswordForm(data=dict(form_data))

        if not form.validate():
            return ApiResponse(
                success=False,
                error=' '.join(error for errors in form.errors.values() for error in errors)
            )

        is_valid = await validate_password_async(current_user.id, form.password.data, db)

        if not is_valid:
            return ApiResponse(success=False, error='密码验证失败')

        # 设置临时标记允许用户访问密码更改页面
        from src.extensions import cache
        cache_key = f"password_change_verified_{current_user.id}"
        cache.set(cache_key, True, timeout=600)

        return ApiResponse(
            success=True,
            data={
                'message': '密码验证成功',
                'redirect_url': '/my/pw/change'
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"密码确认失败: {str(e)}")


@router.get("/me/security/change-password")
async def change_password_form_api(current_user: UserModel = Depends(jwt_required_dependency)):
    """更改密码表单API"""
    from src.extensions import cache
    cache_key = f"password_change_verified_{current_user.id}"

    if not cache.get(cache_key):
        return ApiResponse(
            success=False,
            error='请先验证当前密码',
            data={'redirect_url': '/my/pw/confirm'}
        )

    return ApiResponse(
        success=True,
        data={
            "form_type": 'change',
            "user_id": current_user.id
        }
    )


@router.put("/me/security/change-password")
async def change_password_api(
        request: Request,
        current_user: UserModel = Depends(_get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """更改密码API"""
    try:
        from utils.security.forms import ChangePasswordForm
        from src.api.v1.user_utils.password_utils import validate_password_async

        form_data = await request.form()
        form = ChangePasswordForm(data=dict(form_data))

        if not form.validate():
            return ApiResponse(
                success=False,
                error=' '.join(error for errors in form.errors.values() for error in errors)
            )

        # 验证当前密码是否正确
        is_valid = await validate_password_async(
            current_user.id,
            form.current_password.data,
            db
        )

        if not is_valid:
            return ApiResponse(success=False, error='当前密码不正确')

        ip = get_client_ip(request)
        success = await update_password(
            current_user.id,
            new_password=form.new_password.data,
            confirm_password=form.confirm_password.data,
            ip=ip,
            db=db
        )

        if not success:
            return ApiResponse(success=False, error='密码修改失败')

        # 清除临时标记
        from src.extensions import cache
        cache_key = f"password_change_verified_{current_user.id}"
        cache.delete(cache_key)

        return ApiResponse(
            success=True,
            data={'message': '密码修改成功！现在需要重新登录。'}
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"密码修改失败: {str(e)}")


@router.put("/setting/profiles")
async def update_setting_profiles(
        request: Request,
        current_user: UserModel = Depends(_get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """更新设置资料API"""
    try:
        from src.extensions import cache
        result = await change_profiles_back(
            request=request,
            user_id=current_user.id,
            cache_instance=cache,
            domain=app_config.domain,
            db=db
        )
        return result
    except Exception as e:
        return ApiResponse(success=False, error=f"更新设置失败: {str(e)}")


@router.put("/users/{user_id}/roles")
async def assign_roles_to_user(
        user_id: int,
        request: Request,
        current_user: UserModel = Depends(_get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """为用户分配角色（管理员专用）"""
    try:
        # 检查管理员权限
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(status_code=403, detail="权限不足")

        body = await request.json()
        role_ids = body.get('role_ids', [])

        # 验证用户是否存在
        user_query = select(UserModel).where(UserModel.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            return ApiResponse(success=False, error="用户不存在")

        # 清除该用户现有的角色分配
        from shared.models.user_role import UserRole
        delete_query = UserRole.__table__.delete().where(UserRole.user_id == user_id)
        await db.execute(delete_query)

        # 添加新的角色分配
        if role_ids:
            from datetime import datetime
            for role_id in role_ids:
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by=current_user.id,
                    created_at=datetime.now()
                )
                db.add(user_role)

        await db.commit()

        return ApiResponse(
            success=True,
            data={"message": "角色分配成功"},
            message="角色分配成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        print(f"Error in assign_roles_to_user: {e}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"分配角色失败: {str(e)}")
