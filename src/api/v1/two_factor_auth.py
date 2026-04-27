"""
双因素认证(2FA)管理API
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.two_factor_auth import two_factor_auth
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["2fa"])


class Enable2FARequest(BaseModel):
    """启用2FA请求"""
    totp_token: str  # TOTP验证码用于验证


class Verify2FALoginRequest(BaseModel):
    """2FA登录验证请求"""
    user_id: int
    token: str  # TOTP或备用码


@router.get("/2fa/setup")
async def setup_2fa(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    设置2FA - 生成密钥和QR码
    
    返回QR码供用户扫描,以及手动输入的密钥
    """
    try:
        from shared.models.user import User
        from sqlalchemy import select

        # 获取当前用户
        query = select(User).where(User.id == current_user.id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return ApiResponse(success=False, error="用户不存在")

        if user.is_2fa_enabled:
            return ApiResponse(
                success=False,
                error="2FA已启用",
                data={"is_2fa_enabled": True}
            )

        # 生成新的TOTP密钥
        secret = two_factor_auth.generate_totp_secret()

        # 临时存储到session或缓存(不保存到数据库,直到验证成功)
        from src.extensions import cache
        cache_key = f"2fa_setup:{current_user.id}"
        cache.set(cache_key, secret, ex=600)  # 10分钟过期

        # 生成QR码
        qr_data = two_factor_auth.generate_qr_code(
            secret=secret,
            username=user.username,
            email=user.email
        )

        return ApiResponse(
            success=True,
            data={
                "qr_code": qr_data['qr_code'],
                "secret": qr_data['manual_entry_key'],
                "instructions": [
                    "1. 下载Google Authenticator或类似应用",
                    "2. 扫描二维码或手动输入密钥",
                    "3. 输入应用生成的6位验证码以完成设置"
                ]
            },
            message="请扫描二维码或手动输入密钥"
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"设置2FA失败: {str(e)}")


@router.post("/2fa/enable")
async def enable_2fa(
        request_data: Enable2FARequest,
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    启用2FA
    
    需要用户提供TOTP验证码来验证设置正确
    """
    try:
        from shared.models.user import User
        from sqlalchemy import select
        from src.extensions import cache

        # 获取临时存储的密钥
        cache_key = f"2fa_setup:{current_user.id}"
        secret = cache.get(cache_key)

        if not secret:
            return ApiResponse(success=False, error="设置已过期,请重新开始")

        # 验证TOTP令牌
        if not two_factor_auth.verify_totp(secret, request_data.totp_token):
            return ApiResponse(success=False, error="验证码错误")

        # 生成备用码
        backup_codes = two_factor_auth.generate_backup_codes()

        # 在数据库中启用2FA
        query = select(User).where(User.id == current_user.id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return ApiResponse(success=False, error="用户不存在")

        user.is_2fa_enabled = True
        user.totp_secret = secret
        user.backup_codes = two_factor_auth.hash_backup_codes(backup_codes)

        await db.commit()

        # 清除临时缓存
        cache.delete(cache_key)

        return ApiResponse(
            success=True,
            data={
                "backup_codes": backup_codes,
                "message": "请务必保存这些备用码,它们只能使用一次!"
            },
            message="2FA已成功启用"
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"启用2FA失败: {str(e)}")


@router.post("/2fa/disable")
async def disable_2fa(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    禁用2FA
    """
    try:
        result = two_factor_auth.disable_2fa(current_user.id, db)

        if result['success']:
            return ApiResponse(success=True, message=result['message'])
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"禁用2FA失败: {str(e)}")


@router.post("/2fa/verify-login")
async def verify_2fa_login(
        request_data: Verify2FALoginRequest,
        db: AsyncSession = Depends(get_async_db)
):
    """
    验证2FA登录
    
    在用户输入用户名密码后,如果启用了2FA,需要调用此接口
    """
    try:
        result = two_factor_auth.verify_2fa_login(
            user_id=request_data.user_id,
            token=request_data.token,
            db_session=db
        )

        if result['success']:
            return ApiResponse(
                success=True,
                data={
                    "method": result['method'],
                    "message": "2FA验证成功,可以完成登录"
                }
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"2FA验证失败: {str(e)}")


@router.post("/2fa/backup-codes/regenerate")
async def regenerate_backup_codes(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    重新生成备用码
    """
    try:
        result = two_factor_auth.regenerate_backup_codes(current_user.id, db)

        if result['success']:
            return ApiResponse(
                success=True,
                data={
                    "backup_codes": result['backup_codes'],
                    "message": "旧备用码已失效,请保存新备用码"
                },
                message="备用码已重新生成"
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"重新生成备用码失败: {str(e)}")


@router.get("/2fa/status")
async def get_2fa_status(
        db: AsyncSession = Depends(get_async_db),
        current_user=Depends(jwt_required)
):
    """
    获取2FA状态
    """
    try:
        from shared.models.user import User
        from sqlalchemy import select

        query = select(User).where(User.id == current_user.id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return ApiResponse(success=False, error="用户不存在")

        return ApiResponse(
            success=True,
            data={
                "is_2fa_enabled": user.is_2fa_enabled,
                "has_backup_codes": bool(user.backup_codes),
                "username": user.username,
                "email": user.email
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取2FA状态失败: {str(e)}")
