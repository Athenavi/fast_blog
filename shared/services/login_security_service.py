"""
登录安全管理服务
提供登录尝试记录、频繁失败检测、账户锁定等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from sqlalchemy import select, func, delete

from shared.models.login_attempt import LoginAttempt
from src.utils.database.main import get_async_session_context

logger = logging.getLogger(__name__)


class LoginSecurityService:
    """登录安全服务"""

    # 配置常量
    MAX_FAILED_ATTEMPTS = 5  # 最大失败次数
    LOCKOUT_DURATION_MINUTES = 30  # 锁定时长（分钟）
    CHECK_WINDOW_MINUTES = 15  # 检查窗口期（分钟）

    async def record_login_attempt_async(
            self,
            username: str,
            ip_address: str,
            user_agent: Optional[str] = None,
            is_success: bool = False,
            failure_reason: Optional[str] = None
    ):
        """
        异步记录登录尝试（用于 FastAPI 异步端点）
        """
        from sqlalchemy import insert

        async with get_async_session_context() as session:
            stmt = insert(LoginAttempt).values(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                is_success=is_success,
                failure_reason=failure_reason,
                created_at=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()

        logger.info(
            f"Login attempt recorded (async): username={username}, ip={ip_address}, "
            f"success={is_success}, reason={failure_reason}"
        )

    async def check_account_locked_async(self, username: str) -> Tuple[bool, Optional[datetime]]:
        """
        异步检查账户是否被锁定（用于 FastAPI 异步端点）
        """
        # 计算检查窗口的起始时间
        window_start = datetime.utcnow() - timedelta(minutes=self.CHECK_WINDOW_MINUTES)

        async with get_async_session_context() as session:
            # 统计窗口期内的失败次数
            count_stmt = select(func.count()).select_from(LoginAttempt).where(
                LoginAttempt.username == username,
                LoginAttempt.is_success == False,
                LoginAttempt.created_at >= window_start
            )
            result = await session.execute(count_stmt)
            failed_attempts = result.scalar()

            if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                # 获取最后一次失败的时间
                last_failed_stmt = select(LoginAttempt).where(
                    LoginAttempt.username == username,
                    LoginAttempt.is_success == False,
                    LoginAttempt.created_at >= window_start
                ).order_by(LoginAttempt.created_at.desc()).limit(1)

                result = await session.execute(last_failed_stmt)
                last_failed = result.scalar_one_or_none()

                if last_failed:
                    # 计算解锁时间
                    unlock_time = last_failed.created_at + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)

                    # 如果还未到解锁时间，则账户仍被锁定
                    if datetime.utcnow() < unlock_time:
                        logger.warning(f"Account locked (async): {username}, unlock at {unlock_time}")
                        return True, unlock_time

        return False, None

    async def get_failed_attempts_count_async(self, username: str, minutes: int = 15) -> int:
        """
        异步获取指定时间窗口内的失败尝试次数
        """
        window_start = datetime.utcnow() - timedelta(minutes=minutes)

        async with get_async_session_context() as session:
            count_stmt = select(func.count()).select_from(LoginAttempt).where(
                LoginAttempt.username == username,
                LoginAttempt.is_success == False,
                LoginAttempt.created_at >= window_start
            )
            result = await session.execute(count_stmt)
            return result.scalar()

    async def get_recent_failed_attempts_async(
            self,
            username: Optional[str] = None,
            ip_address: Optional[str] = None,
            limit: int = 50
    ) -> list:
        """
        异步获取最近的失败尝试记录
        
        Args:
            username: 用户名筛选
            ip_address: IP地址筛选
            limit: 返回数量限制
            
        Returns:
            失败尝试记录列表
        """
        async with get_async_session_context() as session:
            query = select(LoginAttempt).where(LoginAttempt.is_success == False)

            if username:
                query = query.where(LoginAttempt.username == username)
            if ip_address:
                query = query.where(LoginAttempt.ip_address == ip_address)

            query = query.order_by(LoginAttempt.created_at.desc()).limit(limit)
            result = await session.execute(query)
            attempts = result.scalars().all()

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

    async def clear_failed_attempts_async(self, username: str) -> int:
        """
        异步清除指定用户的失败尝试记录
        """
        async with get_async_session_context() as session:
            delete_stmt = delete(LoginAttempt).where(
                LoginAttempt.username == username,
                LoginAttempt.is_success == False
            )
            result = await session.execute(delete_stmt)
            await session.commit()
            count = result.rowcount

        logger.info(f"Cleared {count} failed attempts for user (async): {username}")
        return count

    async def cleanup_old_records_async(self, days: int = 30) -> int:
        """
        异步清理旧的登录尝试记录
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        async with get_async_session_context() as session:
            delete_stmt = delete(LoginAttempt).where(
                LoginAttempt.created_at < cutoff_date
            )
            result = await session.execute(delete_stmt)
            await session.commit()
            count = result.rowcount

        logger.info(f"Cleaned up {count} old login attempt records (async)")
        return count

    async def get_security_stats_async(self) -> Dict:
        """
        异步获取安全统计数据
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        async with get_async_session_context() as session:
            # 今日登录尝试总数
            today_total_stmt = select(func.count()).select_from(LoginAttempt).where(
                LoginAttempt.created_at >= today_start
            )
            result = await session.execute(today_total_stmt)
            today_total = result.scalar()

            # 今日失败次数
            today_failed_stmt = select(func.count()).select_from(LoginAttempt).where(
                LoginAttempt.created_at >= today_start,
                LoginAttempt.is_success == False
            )
            result = await session.execute(today_failed_stmt)
            today_failed = result.scalar()

            # 本周失败次数
            week_failed_stmt = select(func.count()).select_from(LoginAttempt).where(
                LoginAttempt.created_at >= week_start,
                LoginAttempt.is_success == False
            )
            result = await session.execute(week_failed_stmt)
            week_failed = result.scalar()

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
