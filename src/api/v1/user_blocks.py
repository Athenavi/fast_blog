"""
用户屏蔽/拉黑 API
提供屏蔽、取消屏蔽、检查屏蔽状态等功能
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user_block import UserBlock
from shared.models.user import User
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/blocks", tags=["user-blocks"])


@router.post("/block/{blocked_user_id}")
async def block_user(
        blocked_user_id: int,
        reason: Optional[str] = Query(None, description="屏蔽原因"),
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    屏蔽/拉黑指定用户
    
    Args:
        blocked_user_id: 被屏蔽用户ID
        reason: 屏蔽原因(可选)
    """
    try:
        # 不能屏蔽自己
        if blocked_user_id == current_user_id:
            return ApiResponse(success=False, error="不能屏蔽自己")

        # 验证被屏蔽用户是否存在
        user_query = select(User).where(User.id == blocked_user_id)
        user_result = await db.execute(user_query)
        blocked_user = user_result.scalar_one_or_none()

        if not blocked_user:
            return ApiResponse(success=False, error="用户不存在")

        # 检查是否已经屏蔽
        existing_query = select(UserBlock).where(
            and_(
                UserBlock.blocker == current_user_id,
                UserBlock.blocked_user == blocked_user_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing_block = existing_result.scalar_one_or_none()

        if existing_block:
            return ApiResponse(success=False, error="已经屏蔽了该用户")

        # 创建屏蔽记录
        new_block = UserBlock(
            blocker=current_user_id,
            blocked_user=blocked_user_id,
            reason=reason,
            created_at=datetime.now()
        )

        db.add(new_block)
        await db.commit()

        return ApiResponse(
            success=True,
            message="屏蔽成功"
        )

    except Exception as e:
        import traceback
        print(f"Error in block_user: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.delete("/unblock/{blocked_user_id}")
async def unblock_user(
        blocked_user_id: int,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    取消屏蔽指定用户
    
    Args:
        blocked_user_id: 被取消屏蔽的用户ID
    """
    try:
        # 查询屏蔽记录
        query = select(UserBlock).where(
            and_(
                UserBlock.blocker == current_user_id,
                UserBlock.blocked_user == blocked_user_id
            )
        )
        result = await db.execute(query)
        block_record = result.scalar_one_or_none()

        if not block_record:
            return ApiResponse(success=False, error="未找到屏蔽记录")

        # 删除屏蔽记录
        await db.delete(block_record)
        await db.commit()

        return ApiResponse(
            success=True,
            message="取消屏蔽成功"
        )

    except Exception as e:
        import traceback
        print(f"Error in unblock_user: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/check/{user_id}")
async def check_block_status(
        user_id: int,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    检查是否屏蔽了指定用户
    
    Args:
        user_id: 要检查的用户ID
    """
    try:
        query = select(UserBlock).where(
            and_(
                UserBlock.blocker == current_user_id,
                UserBlock.blocked_user == user_id
            )
        )
        result = await db.execute(query)
        block_record = result.scalar_one_or_none()

        return ApiResponse(
            success=True,
            data={
                "is_blocked": block_record is not None,
                "blocked_at": block_record.created_at.isoformat() if block_record else None,
                "reason": block_record.reason if block_record else None
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in check_block_status: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/list")
async def get_blocked_users(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取我屏蔽的用户列表
    
    Args:
        page: 页码
        per_page: 每页数量
    """
    try:
        offset = (page - 1) * per_page

        # 查询总数
        count_query = (
            select(__import__('sqlalchemy').func.count())
            .select_from(UserBlock)
            .where(UserBlock.blocker == current_user_id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询屏蔽列表
        query = (
            select(UserBlock, User.username, User.profile_picture)
            .join(User, UserBlock.blocked_user == User.id)
            .where(UserBlock.blocker == current_user_id)
            .order_by(UserBlock.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        result = await db.execute(query)
        blocked_list = []

        for row in result.fetchall():
            block_record = row[0]
            blocked_list.append({
                "block_id": block_record.id,
                "user_id": block_record.blocked_user,
                "username": row[1],
                "avatar": row[2],
                "reason": block_record.reason,
                "blocked_at": block_record.created_at.isoformat()
            })

        return ApiResponse(
            success=True,
            data={
                "blocked_users": blocked_list,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_blocked_users: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/blocked-me")
async def get_users_who_blocked_me(
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取屏蔽了我的用户列表(用于隐私保护,只返回数量)
    """
    try:
        # 查询总数
        count_query = (
            select(__import__('sqlalchemy').func.count())
            .select_from(UserBlock)
            .where(UserBlock.blocked_user == current_user_id)
        )
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0

        return ApiResponse(
            success=True,
            data={
                "blocked_by_count": count
            }
        )

    except Exception as e:
        import traceback
        print(f"Error in get_users_who_blocked_me: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
