"""
邮箱验证服务
提供邮箱验证码发送、验证等功能
"""

import logging
import random
import string
from datetime import datetime

from shared.utils.response import ApiResponse

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """邮箱验证服务"""

    # 配置常量
    CODE_LENGTH = 6  # 验证码长度
    EXPIRE_MINUTES = 10  # 验证码有效期（分钟）
    MAX_ATTEMPTS = 5  # 最大验证尝试次数
    RESEND_INTERVAL_SECONDS = 60  # 重发间隔（秒）

    def __init__(self):
        # 使用内存存储验证码（生产环境应使用Redis）
        self._verification_codes = {}

    def generate_code(self) -> str:
        """生成随机验证码"""
        return ''.join(random.choices(string.digits, k=self.CODE_LENGTH))

    def send_verification_code(self, email: str) -> dict:
        """
        发送邮箱验证码
        
        Args:
            email: 邮箱地址
            
        Returns:
            包含成功状态和消息的字典
        """
        # 检查是否可以重发
        if email in self._verification_codes:
            last_sent = self._verification_codes[email]['sent_at']
            elapsed = (datetime.utcnow() - last_sent).total_seconds()

            if elapsed < self.RESEND_INTERVAL_SECONDS:
                remaining = int(self.RESEND_INTERVAL_SECONDS - elapsed)
                return {
                    'success': False,
                    'message': f'请稍后再试，{remaining}秒后可重新发送',
                    'can_resend_in': remaining
                }

        # 生成验证码
        code = self.generate_code()

        # TODO: 集成真实的邮件发送服务
        # 这里模拟发送
        logger.info(f"Verification code for {email}: {code}")

        # 存储验证码
        self._verification_codes[email] = {
            'code': code,
            'sent_at': datetime.utcnow(),
            'attempts': 0,
            'verified': False
        }

        return {
            'success': True,
            'message': '验证码已发送到您的邮箱',
            'expire_minutes': self.EXPIRE_MINUTES
        }

    def verify_code(self, email: str, code: str) -> dict:
        """
        验证邮箱验证码
        
        Args:
            email: 邮箱地址
            code: 验证码
            
        Returns:
            包含验证结果的字典
        """
        # 检查是否有验证码记录
        if email not in self._verification_codes:
            return {
                'success': False,
                'message': '请先获取验证码'
            }

        record = self._verification_codes[email]

        # 检查是否已验证
        if record['verified']:
            return {
                'success': False,
                'message': '该验证码已被使用'
            }

        # 检查尝试次数
        if record['attempts'] >= self.MAX_ATTEMPTS:
            return {
                'success': False,
                'message': '验证次数过多，请重新获取验证码'
            }

        # 检查是否过期
        elapsed = (datetime.utcnow() - record['sent_at']).total_seconds()
        if elapsed > self.EXPIRE_MINUTES * 60:
            # 清除过期的验证码
            del self._verification_codes[email]
            return {
                'success': False,
                'message': '验证码已过期，请重新获取'
            }

        # 增加尝试次数
        record['attempts'] += 1

        # 验证验证码
        if record['code'] != code:
            remaining_attempts = self.MAX_ATTEMPTS - record['attempts']
            return {
                'success': False,
                'message': f'验证码错误，还剩 {remaining_attempts} 次机会',
                'remaining_attempts': remaining_attempts
            }

        # 验证成功
        record['verified'] = True
        record['verified_at'] = datetime.utcnow()

        return {
            'success': True,
            'message': '验证成功'
        }

    def is_verified(self, email: str) -> bool:
        """
        检查邮箱是否已验证
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否已验证
        """
        if email not in self._verification_codes:
            return False

        return self._verification_codes[email].get('verified', False)

    def cleanup_expired_codes(self) -> int:
        """
        清理过期的验证码
        
        Returns:
            清理的数量
        """
        now = datetime.utcnow()
        expired_emails = []

        for email, record in self._verification_codes.items():
            elapsed = (now - record['sent_at']).total_seconds()
            if elapsed > self.EXPIRE_MINUTES * 60:
                expired_emails.append(email)

        for email in expired_emails:
            del self._verification_codes[email]

        logger.info(f"Cleaned up {len(expired_emails)} expired verification codes")
        return len(expired_emails)


# 全局实例
email_verification_service = EmailVerificationService()
