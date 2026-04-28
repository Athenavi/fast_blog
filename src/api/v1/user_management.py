"""
用户管理 API（基于 PyJWT + SQLAlchemy，无 fastapi-jwt-auth 依赖）
"""
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.user_settings import change_profiles_back
# SQLAlchemy 模型与服务（保持不变）
from shared.models.user import User as UserModel
from shared.services import create_user_account
from src.api.v1.responses import ApiResponse
from src.api.v1.user_utils.password_utils import update_password, validate_password_async
from src.auth.auth_deps import authenticate_user_with_session
from src.extensions import get_async_db_session as get_async_db
from src.setting import app_config, settings
from src.utils.security.ip_utils import get_client_ip
from src.utils.token_blacklist import token_blacklist

router = APIRouter(prefix="/management", tags=["user-management"])


# ---------------------------------------------------------------------------
# JWT 工具函数
# ---------------------------------------------------------------------------

def create_jwt_token(
        subject: str,
        token_type: str = "access",
        expires_delta: Optional[timedelta] = None
) -> str:
    """生成 JWT（包含标准声明 sub, exp, jti, type）"""
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """解码并验证 JWT，返回 payload。若无效抛出 HTTPException"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        return payload
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extract_token_from_request(request: Request) -> Optional[str]:
    """从 Authorization header 或 cookie 中提取 JWT"""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    # 兼容 cookie，名称根据你的需求调整
    return request.cookies.get("access_token") or request.cookies.get("access_token_cookie")


# ---------------------------------------------------------------------------
# FastAPI 依赖：获取当前用户
# ---------------------------------------------------------------------------

async def get_current_active_user(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
) -> UserModel:
    """获取当前活跃用户（强制验证）"""
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_jwt_token(token)

    # 提取用户 ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )

    # 黑名单检查
    jti = payload.get("jti")
    if jti and token_blacklist.is_available and token_blacklist.is_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # 加载用户
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


async def get_current_user_optional(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
) -> Optional[UserModel]:
    """可选获取当前用户（未登录时返回 None）"""
    token = extract_token_from_request(request)
    if not token:
        return None
    try:
        payload = decode_jwt_token(token)
    except HTTPException:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    # 黑名单检查
    jti = payload.get("jti")
    if jti and token_blacklist.is_available and token_blacklist.is_blacklisted(jti):
        return None

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


# 向后兼容的别名
get_current_user = get_current_active_user
jwt_required = get_current_active_user  # 相当于原 jwt_required 依赖
jwt_optional = get_current_user_optional  # 相当于原 jwt_optional 函数


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
        "created_at": article.created_at.isoformat() if hasattr(article.created_at,
                                                                "isoformat") else article.created_at,
        "updated_at": article.updated_at.isoformat() if hasattr(article.updated_at,
                                                                "isoformat") else article.updated_at,
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
):
    """使用用户名或邮箱登录，返回 access / refresh token（PyJWT）"""
    # 1. 验证凭证
    user = await authenticate_user_with_session(username, password, db)
    if not user:
        return ApiResponse(success=False, error="用户名或密码错误")
    if not user.is_active:
        return ApiResponse(success=False, error="账户已被禁用")

    # 2. 生成 JWT
    access_token = create_jwt_token(subject=str(user.id), token_type="access")
    refresh_token = create_jwt_token(subject=str(user.id), token_type="refresh")

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
    access_token = create_jwt_token(subject=str(user.id), token_type="access")
    refresh_token = create_jwt_token(subject=str(user.id), token_type="refresh")

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
async def logout_api(request: Request):
    """将当前 access_token 及可选的 refresh_token 加入黑名单"""
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        access_token_str = data.get("access_token")
        refresh_token_str = data.get("refresh_token")

        # 辅助函数：将 token 加入黑名单
        def _blacklist_token(token: str):
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": False},  # 允许已过期的 token 也能被撤销
                )
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                    token_blacklist.add_to_blacklist(jti, expires_at)
            except Exception:
                pass

        if access_token_str:
            _blacklist_token(access_token_str)
        if refresh_token_str:
            _blacklist_token(refresh_token_str)

        return ApiResponse(success=True, message="登出成功")
    except Exception as e:
        return ApiResponse(success=False, error="登出失败，请稍后重试")


@router.post("/auth/token/refresh", summary="刷新访问令牌")
async def refresh_token_api(request: Request):
    """使用 refresh_token 获取新的 access_token（支持可选的 refresh token 轮换）"""
    try:
        body = await request.body()
        data = json.loads(body)
        refresh_token_str = data.get("refresh")
        if not refresh_token_str:
            return ApiResponse(success=False, error="缺少 refresh token")

        # 解码并验证 refresh token
        payload = decode_jwt_token(refresh_token_str)
        if payload.get("type") != "refresh":
            return ApiResponse(success=False, error="不是有效的 refresh token")

        user_id = payload.get("sub")
        if not user_id:
            return ApiResponse(success=False, error="无效的 refresh token")

        # 生成新的 access token（以及可选的 refresh token 轮换）
        new_access_token = create_jwt_token(subject=user_id, token_type="access")
        new_refresh_token = refresh_token_str  # 默认不轮换
        # 如果需要轮换，取消注释以下代码块：
        # new_refresh_token = create_jwt_token(subject=user_id, token_type="refresh")
        # # 将旧的 refresh token 加入黑名单
        # old_jti = payload.get("jti")
        # old_exp = payload.get("exp")
        # if old_jti and old_exp:
        #     token_blacklist.add_to_blacklist(
        #         old_jti,
        #         datetime.fromtimestamp(old_exp, tz=timezone.utc)
        #     )

        return ApiResponse(
            success=True,
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
            },
            message="Token refreshed successfully",
        )
    except HTTPException as e:
        # decode_jwt_token 会抛出 401，但这里我们想返回 ApiResponse 格式
        return ApiResponse(success=False, error=e.detail)
    except Exception:
        return ApiResponse(success=False, error="Token 刷新失败，请稍后重试")


# ---------------------------------------------------------------------------
# 用户资料与设置 API
# ---------------------------------------------------------------------------

@router.get("/me/profile")
async def get_my_profile_api(
        request: Request,
        current_user: UserModel = Depends(get_current_active_user),
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

    # 文章与统计
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
        current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """查看指定用户的公开资料"""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        return ApiResponse(success=False, error="用户未找到")

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
