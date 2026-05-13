"""
认证相关 API
包含用户名/邮箱检查、登录、注册等功能
"""
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.extensions import get_async_db_session as get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/check-username")
async def check_username(username: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    """检查用户名是否可用"""
    try:
        existing = await db.scalar(
            select(User).where(func.lower(User.username) == func.lower(username))
        )
        return JSONResponse({
            "success": True,
            "available": existing is None,
            "exists": existing is not None
        })
    except Exception as e:
        logger.error(f"Check username error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/check-email")
async def check_email(email: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    """检查邮箱是否可用"""
    try:
        existing = await db.scalar(
            select(User).where(func.lower(User.email) == func.lower(email))
        )
        return JSONResponse({
            "success": True,
            "available": existing is None,
            "exists": existing is not None
        })
    except Exception as e:
        logger.error(f"Check email error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
