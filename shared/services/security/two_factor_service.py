"""
TOTP 双因素认证服务
支持 TOTP 验证、2FA 启用/禁用、备用码管理
"""
import hashlib
import hmac
import struct
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.unified_logger import default_logger as logger


BACKUP_CODE_COUNT = 8
BACKUP_CODE_LENGTH = 10
TOTP_ISSUER = "FastBlog"


class TwoFactorService:
    """双因素认证服务"""

    async def setup_totp(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Dict:
        """
        初始化 TOTP 双因素认证

        生成 TOTP 密钥和备用码

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            包含密钥、QR 码 URI 和备用码的字典
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "用户不存在"}

        # 生成 TOTP 密钥
        secret = pyotp.random_base32()
        username = user.username or user.email or f"user_{user_id}"

        # 创建 TOTP URI（用于生成 QR 码）
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name=TOTP_ISSUER,
        )

        # 存储密钥（标记为未验证）
        user.totp_secret = secret
        user.is_2fa_enabled = False  # 待验证后才启用
        await db.commit()

        # 生成备用码
        backup_codes = self._generate_backup_codes()

        return {
            "success": True,
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "backup_codes": backup_codes,
            "message": "请使用 Authenticator 应用扫描二维码，然后调用 verify_totp 完成验证",
        }

    async def verify_and_enable(
        self,
        db: AsyncSession,
        user_id: int,
        code: str,
    ) -> Dict:
        """
        验证 TOTP 码并启用 2FA

        Args:
            db: 数据库会话
            user_id: 用户 ID
            code: 用户输入的 TOTP 验证码

        Returns:
            操作结果
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "用户不存在"}

        if not user.totp_secret:
            return {"success": False, "error": "请先调用 setup_totp 初始化"}

        if user.is_2fa_enabled:
            return {"success": False, "error": "双因素认证已启用"}

        # 验证 TOTP 码
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            return {"success": False, "error": "验证码无效，请重试"}

        # 生成备用码并启用
        backup_codes = self._generate_backup_codes()
        user.backup_codes = "\n".join(backup_codes)
        user.is_2fa_enabled = True
        await db.commit()

        return {
            "success": True,
            "message": "双因素认证已启用",
            "backup_codes": backup_codes,
            "warning": "请妥善保管备用码，每个备用码只能使用一次",
        }

    async def verify(
        self,
        db: AsyncSession,
        user_id: int,
        code: str,
    ) -> Dict:
        """
        验证 TOTP 验证码（登录时使用）

        支持 TOTP 码和备用码两种方式

        Args:
            db: 数据库会话
            user_id: 用户 ID
            code: TOTP 验证码或备用码

        Returns:
            验证结果
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "用户不存在"}

        if not user.is_2fa_enabled:
            return {"success": True, "message": "2FA 未启用"}

        # 尝试 TOTP 验证
        if user.totp_secret:
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code, valid_window=1):
                return {"success": True, "method": "totp"}

        # 尝试备用码
        if user.backup_codes:
            backup_list = user.backup_codes.split("\n")
            for i, backup_code in enumerate(backup_list):
                backup_code = backup_code.strip()
                # 使用恒定时间比较
                if self._constant_time_compare(code.strip(), backup_code):
                    # 移除已使用的备用码
                    remaining = backup_list[:i] + backup_list[i + 1:]
                    user.backup_codes = "\n".join(remaining) if remaining else None
                    await db.commit()
                    return {"success": True, "method": "backup_code"}

        return {"success": False, "error": "验证码无效"}

    async def disable(
        self,
        db: AsyncSession,
        user_id: int,
        password_verified: bool = False,
    ) -> Dict:
        """
        禁用双因素认证

        Args:
            db: 数据库会话
            user_id: 用户 ID
            password_verified: 是否已验证密码

        Returns:
            操作结果
        """
        if not password_verified:
            return {"success": False, "error": "需要验证密码后才能关闭 2FA"}

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "用户不存在"}

        user.totp_secret = None
        user.backup_codes = None
        user.is_2fa_enabled = False
        await db.commit()

        return {"success": True, "message": "双因素认证已关闭"}

    async def regenerate_backup_codes(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Dict:
        """
        重新生成备用码

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            新的备用码列表
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"success": False, "error": "用户不存在"}

        if not user.is_2fa_enabled:
            return {"success": False, "error": "2FA 未启用"}

        backup_codes = self._generate_backup_codes()
        user.backup_codes = "\n".join(backup_codes)
        await db.commit()

        return {
            "success": True,
            "backup_codes": backup_codes,
        }

    def _generate_backup_codes(self) -> List[str]:
        """生成备用码列表"""
        import secrets
        codes = []
        for _ in range(BACKUP_CODE_COUNT):
            code = secrets.token_hex(BACKUP_CODE_LENGTH // 2).upper()
            # 格式化为 xxxx-xxxx
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes

    def _constant_time_compare(self, a: str, b: str) -> bool:
        """恒定时间字符串比较，防止时序攻击"""
        return hmac.compare_digest(a.encode(), b.encode())


# 全局实例
two_factor_service = TwoFactorService()

__all__ = ['TwoFactorService', 'two_factor_service']
