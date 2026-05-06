"""
登录安全管理服务
提供登录尝试记录、频繁失败检测、账户锁定等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from shared.models.login_attempt import LoginAttempt
from src.extensions import db

logger = logging.getLogger(__name__)


class LoginSecurityService:
    """登录安全服务"""

    # 配置常量
    MAX_FAILED_ATTEMPTS = 5  # 最大失败次数
    LOCKOUT_DURATION_MINUTES = 30  # 锁定时长（分钟）
    CHECK_WINDOW_MINUTES = 15  # 检查窗口期（分钟）

    def record_login_attempt(
            self,
            username: str,
            ip_address: str,
            user_agent: Optional[str] = None,
            is_success: bool = False,
            failure_reason: Optional[str] = None
    ) -> LoginAttempt:
        """
        记录登录尝试
        
        Args:
            username: 用户名
            ip_address: IP地址
            user_agent: User-Agent
            is_success: 是否成功
            failure_reason: 失败原因
            
        Returns:
            创建的登录尝试记录
        """
        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            is_success=is_success,
            failure_reason=failure_reason,
            created_at=datetime.utcnow()
        )

        db.session.add(attempt)
        db.session.commit()

        logger.info(
            f"Login attempt recorded: username={username}, ip={ip_address}, "
            f"success={is_success}, reason={failure_reason}"
        )

        return attempt

    def check_account_locked(self, username: str) -> Tuple[bool, Optional[datetime]]:
        """
        检查账户是否被锁定
        
        Args:
            username: 用户名
            
        Returns:
            (是否锁定, 解锁时间)
        """
        # 计算检查窗口的起始时间
        window_start = datetime.utcnow() - timedelta(minutes=self.CHECK_WINDOW_MINUTES)

        # 统计窗口期内的失败次数
        failed_attempts = LoginAttempt.query.filter(
            LoginAttempt.username == username,
            LoginAttempt.is_success == False,
            LoginAttempt.created_at >= window_start
        ).count()

        if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            # 获取最后一次失败的时间
            last_failed = LoginAttempt.query.filter(
                LoginAttempt.username == username,
                LoginAttempt.is_success == False,
                LoginAttempt.created_at >= window_start
            ).order_by(LoginAttempt.created_at.desc()).first()

            if last_failed:
                # 计算解锁时间
                unlock_time = last_failed.created_at + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)

                # 如果还未到解锁时间，则账户仍被锁定
                if datetime.utcnow() < unlock_time:
                    logger.warning(f"Account locked: {username}, unlock at {unlock_time}")
                    return True, unlock_time

        return False, None

    def get_failed_attempts_count(self, username: str, minutes: int = 15) -> int:
        """
        获取指定时间窗口内的失败尝试次数
        
        Args:
            username: 用户名
            minutes: 时间窗口（分钟）
            
        Returns:
            失败尝试次数
        """
        window_start = datetime.utcnow() - timedelta(minutes=minutes)

        count = LoginAttempt.query.filter(
            LoginAttempt.username == username,
            LoginAttempt.is_success == False,
            LoginAttempt.created_at >= window_start
        ).count()

        return count

    def get_recent_failed_attempts(
            self,
            username: Optional[str] = None,
            ip_address: Optional[str] = None,
            limit: int = 50
    ) -> list:
        """
        获取最近的失败尝试记录
        
        Args:
            username: 用户名筛选
            ip_address: IP地址筛选
            limit: 返回数量限制
            
        Returns:
            失败尝试记录列表
        """
        query = LoginAttempt.query.filter_by(is_success=False)

        if username:
            query = query.filter_by(username=username)
        if ip_address:
            query = query.filter_by(ip_address=ip_address)

        attempts = query.order_by(LoginAttempt.created_at.desc()).limit(limit).all()

        return [
            {
                'id': attempt.id,
                'username': attempt.username,
                'ip_address': attempt.ip_address,
                'user_agent': attempt.user_agent,
                'failure_reason': attempt.failure_reason,
                'created_at': attempt.created_at.isoformat() if attempt.created_at else None
            }
            for attempt in attempts
        ]

    def clear_failed_attempts(self, username: str) -> int:
        """
        清除指定用户的失败尝试记录
        
        Args:
            username: 用户名
            
        Returns:
            清除的记录数
        """
        count = LoginAttempt.query.filter_by(
            username=username,
            is_success=False
        ).delete()

        db.session.commit()
        logger.info(f"Cleared {count} failed attempts for user: {username}")
        return count

    def cleanup_old_records(self, days: int = 30) -> int:
        """
        清理旧的登录尝试记录
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        count = LoginAttempt.query.filter(
            LoginAttempt.created_at < cutoff_date
        ).delete()

        db.session.commit()
        logger.info(f"Cleaned up {count} old login attempt records")
        return count

    def get_security_stats(self) -> Dict:
        """
        获取安全统计数据
        
        Returns:
            统计数据字典
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        # 今日登录尝试总数
        today_total = LoginAttempt.query.filter(
            LoginAttempt.created_at >= today_start
        ).count()

        # 今日失败次数
        today_failed = LoginAttempt.query.filter(
            LoginAttempt.created_at >= today_start,
            LoginAttempt.is_success == False
        ).count()

        # 本周失败次数
        week_failed = LoginAttempt.query.filter(
            LoginAttempt.created_at >= week_start,
            LoginAttempt.is_success == False
        ).count()

        # 当前被锁定的账户数（估算）
        locked_accounts = 0
        # 这里简化处理，实际应该遍历所有有失败记录的用户

        return {
            'today_total_attempts': today_total,
            'today_failed_attempts': today_failed,
            'week_failed_attempts': week_failed,
            'locked_accounts_estimate': locked_accounts,
            'max_failed_attempts_threshold': self.MAX_FAILED_ATTEMPTS,
            'lockout_duration_minutes': self.LOCKOUT_DURATION_MINUTES
        }


# 全局实例
login_security_service = LoginSecurityService()
