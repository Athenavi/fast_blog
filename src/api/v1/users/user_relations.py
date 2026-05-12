"""
用户关系管理 API
提供关注/取消关注、粉丝列表、关注列表等功能
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.core.responses import ApiResponse
from shared.models.user import User
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/relations", tags=["user-relations"])

# 使用内存存储关注关系(生产环境应使用数据库)
# 格式: {follower_id: {following_id: timestamp}}
follows_db = {}
# 格式: {user_id: {follower_id: timestamp}}
followers_db = {}


@router.get("/followers")
async def get_followers(
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取当前用户的粉丝列表
    
    Returns:
        粉丝列表及总数
    """
    try:
        # 从内存中获取粉丝
        fans_dict = followers_db.get(current_user.id, {})

        # 构建粉丝列表
        fans_list = []
        for follower_id, follow_time in fans_dict.items():
            # 查询用户信息
            user_query = select(User).where(User.id == int(follower_id))
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if user:
                fans_list.append({
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                        "profile_picture": user.profile_picture
                    },
                    "created_at": datetime.fromtimestamp(follow_time).isoformat()
                })

        # 按关注时间倒序排列
        fans_list.sort(key=lambda x: x['created_at'], reverse=True)

        return ApiResponse(
            success=True,
            data={
                "fans_list": fans_list,
                "fans_count": len(fans_list)
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_followers: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/following")
async def get_following(
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取当前用户关注的用户列表
    
    Returns:
        关注列表及总数
    """
    try:
        # 从内存中获取关注的用户
        following_dict = follows_db.get(current_user.id, {})

        # 构建关注列表
        following_list = []
        for following_id, follow_time in following_dict.items():
            # 查询用户信息
            user_query = select(User).where(User.id == int(following_id))
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if user:
                following_list.append({
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "bio": user.bio,
                        "profile_picture": user.profile_picture
                    },
                    "created_at": datetime.fromtimestamp(follow_time).isoformat()
                })

        # 按关注时间倒序排列
        following_list.sort(key=lambda x: x['created_at'], reverse=True)

        return ApiResponse(
            success=True,
            data={
                "following_list": following_list,
                "following_count": len(following_list)
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_following: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/users")
async def get_users(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有用户列表(用于发现用户)
    
    Returns:
        用户列表及当前用户已关注的用户ID列表
    """
    try:
        offset = (page - 1) * per_page

        # 查询所有用户(排除自己)
        query = (
            select(User)
            .where(User.id != current_user.id)
            .offset(offset)
            .limit(per_page)
        )

        result = await db.execute(query)
        users = result.scalars().all()

        # 获取总数
        count_query = (
            select(func.count())
            .select_from(User)
            .where(User.id != current_user.id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 构建用户列表
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "bio": user.bio,
                "profile_picture": user.profile_picture
            })

        # 获取当前用户已关注的用户ID
        following_dict = follows_db.get(current_user.id, {})
        following_ids = [int(uid) for uid in following_dict.keys()]

        return ApiResponse(
            success=True,
            data={
                "users": user_list,
                "following_ids": following_ids,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_users: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/follow/{target_user_id}")
async def follow_user(
        target_user_id: int,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    关注指定用户
    
    Args:
        target_user_id: 目标用户ID
    """
    try:
        # 不能关注自己
        if target_user_id == current_user.id:
            return ApiResponse(success=False, error="不能关注自己")

        # 验证目标用户是否存在
        user_query = select(User).where(User.id == target_user_id)
        user_result = await db.execute(user_query)
        target_user = user_result.scalar_one_or_none()

        if not target_user:
            return ApiResponse(success=False, error="目标用户不存在")

        # 初始化数据结构
        if current_user.id not in follows_db:
            follows_db[current_user.id] = {}
        if target_user_id not in followers_db:
            followers_db[target_user_id] = {}

        # 检查是否已经关注
        if target_user_id in follows_db[current_user.id]:
            return ApiResponse(success=False, error="已经关注过该用户")

        # 添加关注关系
        current_time = datetime.now().timestamp()
        follows_db[current_user.id][target_user_id] = current_time
        followers_db[target_user_id][current_user.id] = current_time

        # TODO: 发送通知给被关注者

        return ApiResponse(
            success=True,
            data={"message": "关注成功"},
            message="关注成功"
        )

    except Exception as e:
        import traceback
        print(f"Error in follow_user: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/unfollow/{target_user_id}")
async def unfollow_user(
        target_user_id: int,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    取消关注指定用户
    
    Args:
        target_user_id: 目标用户ID
    """
    try:
        # 验证目标用户是否存在
        user_query = select(User).where(User.id == target_user_id)
        user_result = await db.execute(user_query)
        target_user = user_result.scalar_one_or_none()

        if not target_user:
            return ApiResponse(success=False, error="目标用户不存在")

        # 检查是否已关注
        if current_user.id not in follows_db or target_user_id not in follows_db[current_user.id]:
            return ApiResponse(success=False, error="尚未关注该用户")

        # 移除关注关系
        del follows_db[current_user.id][target_user_id]
        if target_user_id in followers_db:
            if current_user.id in followers_db[target_user_id]:
                del followers_db[target_user_id][current_user.id]

        return ApiResponse(
            success=True,
            data={"message": "取消关注成功"},
            message="取消关注成功"
        )

    except Exception as e:
        import traceback
        print(f"Error in unfollow_user: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/counts")
async def get_relation_counts(
        current_user: User = Depends(jwt_required)
):
    """
    获取当前用户的粉丝数和关注数
    
    Returns:
        粉丝数和关注数
    """
    try:
        fans_count = len(followers_db.get(current_user.id, {}))
        following_count = len(follows_db.get(current_user.id, {}))

        return ApiResponse(
            success=True,
            data={
                "fans_count": fans_count,
                "following_count": following_count
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_relation_counts: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
