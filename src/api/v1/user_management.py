"""
用户管理API - 处理用户相关的管理功能
精简优化版本
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.api.v1.user_settings import change_profiles_back
from src.api.v1.user_utils.password_utils import update_password, validate_password_async
from src.api.v1.user_utils.user_entities import get_avatar
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.models import Article
from src.models.user import User as UserModel
from src.setting import app_config
from src.utils.security.ip_utils import get_client_ip

router = APIRouter(prefix="/users", tags=["users"])


def _create_article_response(article):
    """创建文章响应数据的辅助函数"""
    return {
        "id": article.article_id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": article.excerpt,
        "cover_image": article.cover_image,
        "tags": article.tags.split(",") if article.tags else [],
        "views": article.views or 0,
        "likes": article.likes or 0,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat()
    }


def _create_user_response(user):
    """创建用户响应数据的辅助函数"""
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
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat()
    }


async def _get_user_articles(user_id: int, db: AsyncSession, limit: int = 10):
    """获取用户文章"""
    result = await db.execute(
        select(Article)
        .filter(
            Article.user_id == user_id,
            Article.status == 1
        )
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def _get_articles_count(user_id: int, db: AsyncSession):
    """获取用户文章数量"""
    result = await db.execute(
        select(func.count(Article.article_id)).filter(
            Article.user_id == user_id,
            Article.status == 1
        )
    )
    return result.scalar()


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


@router.get("/me/profile")
async def get_my_profile_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """获取我的资料API"""
    try:
        avatar_url = await get_avatar(app_config.domain, current_user.id, 'id', db)

        user_articles = await _get_user_articles(current_user.id, db)
        articles_count = await _get_articles_count(current_user.id, db)

        profile_data = {
            "user": _create_user_response(current_user),
            "recent_articles": [_create_article_response(article) for article in user_articles],
            "stats": _get_user_stats(articles_count),
            "is_following": False,
            "has_unread_message": False
        }

        return ApiResponse(success=True, data=profile_data)
    except Exception as e:
        return ApiResponse(success=False, error=f"获取资料失败: {str(e)}")


@router.get("/{user_id}/profile")
async def get_user_profile_api(
        request: Request,
        user_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """获取用户公共资料API"""
    try:
        # 获取目标用户信息
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        target_user = result.scalar_one_or_none()

        if not target_user:
            return ApiResponse(success=False, error="用户未找到")

        # 获取当前用户ID
        current_user_id = None
        try:
            current_user = await jwt_required(request)
            current_user_id = current_user.id
        except:
            pass

        # 检查隐私设置
        if not await _check_profile_privacy(target_user, current_user_id):
            return ApiResponse(success=False, error="此用户资料是私有的")

        # 获取用户数据
        user_articles = []
        articles_count = 0

        if not target_user.profile_private:
            user_articles = await _get_user_articles(user_id, db)
            articles_count = await _get_articles_count(user_id, db)

        is_following = False
        if current_user_id and current_user_id != user_id:
            # 这里可以添加关注检查逻辑
            pass

        return ApiResponse(
            success=True,
            data={
                "user": _create_user_response(target_user),
                "recent_articles": [_create_article_response(article) for article in user_articles],
                "stats": _get_user_stats(articles_count),
                "is_following": is_following,
                "has_unread_message": False
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=f"获取用户资料失败: {str(e)}")


@router.put("/me/profile")
async def update_my_profile_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新我的资料API"""
    try:
        form_data = await request.form()

        # 更新用户信息
        current_user.username = form_data.get('username', current_user.username)
        current_user.bio = form_data.get('bio', current_user.bio or '')
        current_user.locale = form_data.get('locale', current_user.locale or 'zh_CN')
        current_user.profile_private = form_data.get('profile_private') is not None

        await db.commit()
        await db.refresh(current_user)

        return ApiResponse(
            success=True,
            data={
                "message": "资料更新成功",
                "user": _create_user_response(current_user)
            }
        )
    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"更新资料失败: {str(e)}")


@router.get("/me/security/confirm-password")
async def confirm_password_form_api(current_user=Depends(jwt_required)):
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
        current_user=Depends(jwt_required),
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
async def change_password_form_api(current_user=Depends(jwt_required)):
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
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更改密码API"""
    try:
        from utils.security.forms import ChangePasswordForm

        form_data = await request.form()
        form = ChangePasswordForm(data=dict(form_data))

        if not form.validate():
            return ApiResponse(
                success=False,
                error=' '.join(error for errors in form.errors.values() for error in errors)
            )

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
        current_user=Depends(jwt_required),
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


@router.get("")
async def get_users(
        request: Request,
        current_user=Depends(jwt_required),
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=100),
        search: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_async_db)
):
    """获取所有用户信息（管理员专用）"""
    try:
        # 检查管理员权限
        if not getattr(current_user, 'is_superuser', False):
            raise HTTPException(status_code=403, detail="权限不足")

        # 构建查询条件
        base_query = select(UserModel)
        if search:
            base_query = base_query.where(
                UserModel.username.contains(search) | UserModel.email.contains(search)
            )

        # 获取总数
        total_query = select(func.count()).select_from(UserModel)
        if search:
            total_query = total_query.where(
                UserModel.username.contains(search) | UserModel.email.contains(search)
            )
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 获取分页数据
        offset = (page - 1) * per_page
        users_query = base_query.offset(offset).limit(per_page)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()

        # 构建响应数据
        users_data = []
        for user in users:
            # 这里可以添加计算用户存储使用量的逻辑
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "bio": user.bio,
                "profile_picture": user.profile_picture,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": getattr(user, 'last_login', None),
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "storage_used": 0  # 占位符，实际应计算存储使用量
            })

        return ApiResponse(
            success=True,
            data={
                "users": users_data,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": page < (total + per_page - 1) // per_page,
                    "has_prev": page > 1
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        return ApiResponse(success=False, error=f"获取用户列表失败: {str(e)}")