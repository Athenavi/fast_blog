"""
用户管理 API（完全基于 fastapi-jwt-auth + SQLAlchemy，无 Django 依赖）
"""
import json
import re
from datetime import datetime, timezone
from typing import Optional

import jwt  # fastapi-jwt-auth 内部使用的 PyJWT
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi_jwt_auth import AuthJWT
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# SQLAlchemy 模型与服务
from shared.models.user import User as UserModel
from shared.services import create_user_account
from src.api.v1.responses import ApiResponse
from src.api.v1.user_settings import change_profiles_back
from src.api.v1.user_utils.password_utils import update_password, validate_password_async
from src.auth.auth_deps import (
    authenticate_user_with_session,
    get_current_user,
    jwt_optional,
    jwt_required,
)
from src.extensions import get_async_db_session as get_async_db
from src.setting import app_config
from src.utils.security.ip_utils import get_client_ip
from src.utils.token_blacklist import token_blacklist

router = APIRouter(prefix="/management", tags=["user-management"])


# ---------------------------------------------------------------------------
# 辅助函数：生成 API 响应及格式转换
# ---------------------------------------------------------------------------

def _create_article_response(article):
    """将文章 ORM 对象转换为前端需要的字典"""
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": article.excerpt,
        "cover_image": article.cover_image,
        "tags": [],
        "views": article.views or 0,
        "likes": article.likes or 0,
        "created_at": article.created_at.isoformat() if hasattr(article.created_at, "isoformat") else article.created_at,
        "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at, "isoformat") else article.updated_at,
    }


def _create_user_response(user):
    """将用户 ORM 对象转换为前端需要的字典"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio or "",
        "location": user.locale or "",
        "website": "",
        "profile_private": user.profile_private,
        "display_name": user.username,
        "locale": user.locale or "zh_CN",
        "created_at": user.date_joined if hasattr(user, "date_joined") and user.date_joined else None,
        "updated_at": None,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "vip_level": getattr(user, "vip_level", 0),
        "avatar": user.profile_picture or "",
    }


def _get_user_stats(articles_count: int = 0):
    return {"articles_count": articles_count, "followers_count": 0, "following_count": 0}


# ---------------------------------------------------------------------------
# 认证相关 API
# ---------------------------------------------------------------------------

@router.post("/auth/login", summary="用户登录")
async def login_api(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: AsyncSession = Depends(get_async_db),
    Authorize: AuthJWT = Depends(),
):
    """使用用户名或邮箱登录，返回 access / refresh token（fastapi-jwt-auth）"""
    # 1. 验证凭证
    user = await authenticate_user_with_session(username, password, db)
    if not user:
        return ApiResponse(success=False, error="用户名或密码错误")
    if not user.is_active:
        return ApiResponse(success=False, error="账户已被禁用")

    # 2. 生成 JWT（主题为 user.id 字符串）
    access_token = Authorize.create_access_token(subject=str(user.id))
    refresh_token = Authorize.create_refresh_token(subject=str(user.id))

    # 3. 更新最后登录时间
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
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff,
                "vip_level": getattr(user, "vip_level", 0),
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )


@router.post("/auth/register", summary="用户注册")
async def register_api(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    Authorize: AuthJWT = Depends(),
):
    """用户注册并返回 token"""
    # 基础校验
    if len(username) < 3:
        return ApiResponse(success=False, error="用户名至少需要 3 个字符")
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return ApiResponse(success=False, error="邮箱格式不正确")
    if len(password) < 8:
        return ApiResponse(success=False, error="密码至少需要 8 个字符")
    if not re.search(r"[A-Z]", password):
        return ApiResponse(success=False, error="密码必须包含大写字母")
    if not re.search(r"[a-z]", password):
        return ApiResponse(success=False, error="密码必须包含小写字母")
    if not re.search(r"\d", password):
        return ApiResponse(success=False, error="密码必须包含数字")

    # 检查重名
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    if result.scalar_one_or_none():
        return ApiResponse(success=False, error="用户名已存在")
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    if result.scalar_one_or_none():
        return ApiResponse(success=False, error="邮箱已被注册")

    # 创建用户
    try:
        user = await create_user_account(db=db, username=username, email=email, password=password, is_active=True)
    except ValueError as e:
        return ApiResponse(success=False, error=str(e))

    # 生成 token
    access_token = Authorize.create_access_token(subject=str(user.id))
    refresh_token = Authorize.create_refresh_token(subject=str(user.id))

    return ApiResponse(
        success=True,
        data={
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff,
                "vip_level": getattr(user, "vip_level", 0),
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        message="注册成功",
    )


@router.post("/auth/logout", summary="用户登出")
async def logout_api(
    request: Request,
    Authorize: AuthJWT = Depends(),
):
    """将当前 access_token 及可选的 refresh_token 加入黑名单"""
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        access_token = data.get("access_token")
        refresh_token_str = data.get("refresh_token")

        # 将 access token 加入黑名单
        if access_token:
            try:
                Authorize.jwt_required()  # 确保会解析当前 token
                raw = Authorize.get_raw_jwt()
                jti = raw.get("jti")
                exp = raw.get("exp")
                if jti and exp:
                    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                    token_blacklist.add_to_blacklist(jti, expires_at)
            except Exception:
                pass

        # 将 refresh token 加入黑名单（如果提供）
        if refresh_token_str:
            try:
                # 使用 fastapi-jwt-auth 的配置密钥解码 refresh token
                payload = jwt.decode(
                    refresh_token_str,
                    Authorize._config.authjwt_secret_key,
                    algorithms=[Authorize._config.authjwt_algorithm],
                )
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                    token_blacklist.add_to_blacklist(jti, expires_at)
            except Exception:
                pass

        return ApiResponse(success=True, message="登出成功")
    except Exception as e:
        return ApiResponse(success=False, error="登出失败，请稍后重试")


@router.post("/auth/token/refresh", summary="刷新访问令牌")
async def refresh_token_api(
    request: Request,
    Authorize: AuthJWT = Depends(),
):
    """使用 refresh_token 获取新的 access_token（和可选的 refresh token 轮换）"""
    try:
        body = await request.body()
        data = json.loads(body)
        refresh_token_str = data.get("refresh")
        if not refresh_token_str:
            return ApiResponse(success=False, error="缺少 refresh token")

        # 手动解码 refresh token（使用与 fastapi-jwt-auth 相同的密钥和算法）
        payload = jwt.decode(
            refresh_token_str,
            Authorize._config.authjwt_secret_key,
            algorithms=[Authorize._config.authjwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            return ApiResponse(success=False, error="无效的 refresh token")

        # 生成新的 access token（以及按配置决定是否轮换 refresh token）
        new_access_token = Authorize.create_access_token(subject=user_id)
        new_refresh_token = None
        # 如果配置允许 refresh token 轮换，则创建新 refresh token
        if getattr(Authorize._config, "authjwt_refresh_token_expires", None):
            # fastapi-jwt-auth 默认没有直接接口判断是否轮换，简单起见总是返回相同的 refresh token
            # 若需要轮换可启用：
            # new_refresh_token = Authorize.create_refresh_token(subject=user_id)
            # 同时将旧 refresh token 加入黑名单
            pass

        return ApiResponse(
            success=True,
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token or refresh_token_str,
            },
            message="Token refreshed successfully",
        )
    except jwt.ExpiredSignatureError:
        return ApiResponse(success=False, error="Refresh token 已过期")
    except jwt.InvalidTokenError:
        return ApiResponse(success=False, error="Refresh token 无效")
    except Exception as e:
        return ApiResponse(success=False, error="Token 刷新失败，请稍后重试")


# ---------------------------------------------------------------------------
# 用户资料与设置 API
# ---------------------------------------------------------------------------

@router.get("/me/profile")
async def get_my_profile_api(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取当前登录用户资料"""
    # 头像处理
    avatar_url = None
    if current_user.profile_picture:
        from pathlib import Path
        avatar_dir = Path("static/avatar")
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            f = avatar_dir / f"{current_user.profile_picture}{ext}"
            if f.exists():
                avatar_url = f"{app_config.domain}static/avatar/{current_user.profile_picture}{ext}"
                break
        if not avatar_url:
            avatar_url = f"{app_config.domain}static/avatar/{current_user.profile_picture}.webp"

    # 文章与统计（串行查询，避免同一会话并发）
    from shared.services.article_manager import get_articles_by_user_id, get_article_count_by_user

    articles = await get_articles_by_user_id(db, current_user.id, 10)
    count = await get_article_count_by_user(db, current_user.id)

    profile_data = {
        "user": _create_user_response(current_user),
        "recent_articles": [_create_article_response(a) for a in articles],
        "stats": _get_user_stats(count),
        "is_following": False,
        "has_unread_message": False,
    }
    return ApiResponse(success=True, data=profile_data)


@router.get("/{user_id}/profile")
async def get_user_profile_api(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """查看指定用户的公开资料"""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        return ApiResponse(success=False, error="用户未找到")

    # 可选的当前用户
    current_user = await jwt_optional(request, db, AuthJWT=Depends)
    current_user_id = current_user.id if current_user else None

    if target.profile_private and current_user_id != target.id:
        return ApiResponse(success=False, error="此用户资料是私有的")

    from shared.services.article_manager import get_user_articles_with_pagination

    if target.profile_private:
        articles_list, total_count = [], 0
    else:
        articles_list, total_count = await get_user_articles_with_pagination(
            db=db, user_id=user_id, page=page, per_page=per_page, status=1
        )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

    return ApiResponse(
        success=True,
        data={
            "user": _create_user_response(target),
            "recent_articles": [_create_article_response(a) for a in articles_list],
            "stats": _get_user_stats(total_count),
            "is_following": False,
            "has_unread_message": False,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
    )


@router.put("/me/profile")
async def update_my_profile_api(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """更新当前用户资料"""
    try:
        form = await request.form()
        from shared.services.user_manager import update_user_profile

        updated = await update_user_profile(
            db=db,
            user_id=current_user.id,
            username=form.get("username", current_user.username),
            bio=form.get("bio", current_user.bio or ""),
            locale=form.get("locale", current_user.locale or "zh_CN"),
            profile_private="profile_private" in form,
        )
        if not updated:
            return ApiResponse(success=False, error="用户不存在")
        return ApiResponse(success=True, data={"message": "资料更新成功", "user": _create_user_response(updated)})
    except Exception:
        await db.rollback()
        raise


# ---------------------------------------------------------------------------
# 密码管理 API
# ---------------------------------------------------------------------------

@router.post("/me/security/confirm-password")
async def confirm_password_api(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """验证当前密码，通过后设置允许修改密码的临时标记"""
    from utils.security.forms import ConfirmPasswordForm

    form_data = await request.form()
    form = ConfirmPasswordForm(data=dict(form_data))
    if not form.validate():
        errors = " ".join(e for errs in form.errors.values() for e in errs)
        return ApiResponse(success=False, error=errors)

    valid = await validate_password_async(current_user.id, form.password.data, db)
    if not valid:
        return ApiResponse(success=False, error="密码验证失败")

    # 设置缓存标记（10分钟有效）
    from src.extensions import cache
    cache.set(f"password_change_verified_{current_user.id}", True, timeout=600)
    return ApiResponse(success=True, data={"message": "密码验证成功", "redirect_url": "/my/pw/change"})


@router.put("/me/security/change-password")
async def change_password_api(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """修改密码"""
    from utils.security.forms import ChangePasswordForm

    form_data = await request.form()
    form = ChangePasswordForm(data=dict(form_data))
    if not form.validate():
        errors = " ".join(e for errs in form.errors.values() for e in errs)
        return ApiResponse(success=False, error=errors)

    valid = await validate_password_async(current_user.id, form.current_password.data, db)
    if not valid:
        return ApiResponse(success=False, error="当前密码不正确")

    ip = get_client_ip(request)
    success = await update_password(
        user_id=current_user.id,
        new_password=form.new_password.data,
        confirm_password=form.confirm_password.data,
        ip=ip,
        db=db,
    )
    if not success:
        return ApiResponse(success=False, error="密码修改失败")

    from src.extensions import cache
    cache.delete(f"password_change_verified_{current_user.id}")
    return ApiResponse(success=True, data={"message": "密码修改成功！现在需要重新登录。"})


# ---------------------------------------------------------------------------
# 设置与角色管理 API
# ---------------------------------------------------------------------------

@router.put("/setting/profiles")
async def update_setting_profiles(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """更新用户设置（头像等）"""
    from src.extensions import cache
    result = await change_profiles_back(
        request=request,
        user_id=current_user.id,
        cache_instance=cache,
        domain=app_config.domain,
        db=db,
    )
    return result


@router.put("/users/{user_id}/roles")
async def assign_roles_to_user(
    user_id: int,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """管理员为用户分配角色"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")

    body = await request.json()
    role_ids = body.get("role_ids", [])

    user = await db.get(UserModel, user_id)
    if not user:
        return ApiResponse(success=False, error="用户不存在")

    from shared.models.user_role import UserRole
    # 清除原有角色
    await db.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))
    # 添加新角色
    for rid in role_ids:
        db.add(UserRole(user_id=user_id, role_id=rid, assigned_by=current_user.id, created_at=datetime.now()))
    await db.commit()
    return ApiResponse(success=True, message="角色分配成功")