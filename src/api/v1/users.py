"""
用户相关API
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db
from src.models.user import User

router = APIRouter()

@router.get("/users/profile",
           summary="获取用户资料",
           description="获取当前认证用户的基本资料信息",
           response_description="返回用户资料信息")
async def get_user_profile_api(
    request: Request,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户资料API
    """
    try:
        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": f"{str(request.url).split('/users/profile')[0].rsplit('/', 1)[0]}/static/avatar/{current_user.profile_picture}.webp" if current_user.profile_picture else None,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user.created_at, 'isoformat') else str(current_user.created_at),
            "last_login": getattr(current_user, 'last_login', None),
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "role": getattr(current_user, 'role', 'user')
        }
        
        return ApiResponse(
            success=True,
            data=user_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/users/profile",
           summary="更新用户资料",
           description="更新当前认证用户的基本资料信息",
           response_description="返回更新后的用户资料信息")
async def update_user_profile_api(
    request: Request,
    current_user: User = Depends(jwt_required),
    db: AsyncSession = Depends(get_async_db)
):
    """
    更新用户资料API
    """
    try:
        data = await request.json()
        
        # 更新用户信息
        for field in ['username', 'email', 'avatar']:
            if field in data:
                setattr(current_user, field, data[field])
        
        db.commit()
        db.refresh(current_user)
        
        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": current_user.profile_private,
            "updated_at": current_user.updated_at.isoformat() if hasattr(current_user.updated_at, 'isoformat') else str(current_user.updated_at)
        }
        
        return ApiResponse(
            success=True,
            data=user_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/users",
           summary="获取用户列表",
           description="获取用户列表，支持分页和搜索功能",
           response_description="返回用户列表和分页信息")
async def get_users_list_api(
    request: Request,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100之间"),
    search: str = Query("", description="搜索关键词，用于用户名或邮箱搜索"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户列表API (仅管理员) - 为简单起见，暂时对所有认证用户开放
    """
    try:
        from sqlalchemy import select
        query = select(User)
        
        if search:
            query = query.filter(
                User.username.contains(search) |
                User.email.contains(search)
            )
        
        # 分页
        offset = (page - 1) * per_page
        from sqlalchemy import select
        # 获取总数
        total_query = select(func.count(User.id))
        if search:
            total_query = total_query.where(
                User.username.contains(search) |
                User.email.contains(search)
            )
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        # 获取分页数据
        users_query = select(User)
        if search:
            users_query = users_query.where(
                User.username.contains(search) |
                User.email.contains(search)
            )
        users_query = users_query.offset(offset).limit(per_page)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_superuser": getattr(user, 'is_superuser', False),
                "created_at": user.created_at.isoformat() if hasattr(user.created_at, 'isoformat') else str(user.created_at),
                "last_login": getattr(user, 'last_login', None)
            })
        
        return ApiResponse(
            success=True,
            data=users_data,
            pagination={
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page < (total + per_page - 1) // per_page,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_users_list_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/users/me",
           summary="获取当前用户信息",
           description="获取当前认证用户的详细信息，如果访问令牌即将过期则自动刷新",
           response_description="返回当前用户信息及可能的新访问令牌")
async def get_current_user_api(
    request: Request,
    current_user: User = Depends(jwt_required)
):
    """
    获取当前用户信息，支持自动刷新即将过期的访问令牌
    """
    try:
        # 检查是否在请求处理过程中生成了新的访问令牌
        new_access_token = getattr(request.state, 'new_access_token', None)
        
        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": f"{str(request.url).split('/users/me')[0].rsplit('/', 1)[0]}/static/avatar/{current_user.profile_picture}.webp" if current_user.profile_picture else None,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user.created_at, 'isoformat') else str(current_user.created_at),
            "last_login": getattr(current_user, 'last_login', None)
        }

        response_data = {
            "success": True,
            "data": user_data
        }
        
        # 如果有新的访问令牌，将其添加到响应中
        if new_access_token:
            response_data["new_access_token"] = new_access_token
        
        # 返回JSONResponse以便设置响应头
        response = JSONResponse(content=response_data)
        
        # 如果有新的访问令牌，将其设置在响应头中
        if new_access_token:
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=False,  # 在生产环境中应设为True
                samesite="strict",
                max_age=3600  # 1小时
            )
            
        return response
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})