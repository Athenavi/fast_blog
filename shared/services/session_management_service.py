"""
用户会话管理服务
提供会话管理、设备管理等功能
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from shared.models.user_session import UserSession
from src.extensions import get_async_db_session as get_async_db

logger = logging.getLogger(__name__)


class SessionManagementService:
    """会话管理服务"""

    async def create_session(
            self,
            user_id: int,
            access_token: str,  # access_token
            device_info: Optional[str] = None,
            ip_address: Optional[str] = None,
            location: Optional[str] = None,
            expires_hours: int = 720,  # 默认30天
            db_session=None,
            refresh_token: Optional[str] = None  # refresh_token
    ) -> UserSession:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            access_token: JWT access token
            device_info: 设备信息
            ip_address: IP地址
            location: 地理位置
            expires_hours: 过期时间（小时）
            db_session: 数据库会话（可选）
            refresh_token: JWT refresh token
            
        Returns:
            创建的会话对象
        """
        from src.utils.database.unified_manager import db_manager

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            expires_at = datetime.now() + timedelta(hours=expires_hours)

            session = UserSession(
                user_id=user_id,
                access_token=access_token,  # access_token
                refresh_token=refresh_token,  # refresh_token
                device_info=device_info,
                ip_address=ip_address,
                location=location,
                is_active=True,
                last_activity=datetime.now(),
                expires_at=expires_at,
                created_at=datetime.now()
            )

            db_session.add(session)
            await db_session.commit()
            await db_session.refresh(session)

            logger.info(f"Created new session for user {user_id}")
            return session
        finally:
            if should_close:
                await db_session.close()

    async def get_user_sessions(self, user_id: int, active_only: bool = True, db_session=None) -> List[Dict]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            active_only: 只返回活跃会话
            
        Returns:
            会话列表
        """
        from src.utils.database.unified_manager import db_manager
        from sqlalchemy import select

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            query = select(UserSession).where(UserSession.user_id == user_id)

            if active_only:
                query = query.where(
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now()
                )

            query = query.order_by(UserSession.last_activity.desc())
            result = await db_session.execute(query)
            sessions = result.scalars().all()

            return [self._format_session(s) for s in sessions]
        finally:
            if should_close:
                await db_session.close()

    async def _blacklist_jwt_token(self, token: str, description: str = "token") -> None:
        """
        将 JWT token 加入黑名单
        
        Args:
            token: JWT token 字符串
            description: 描述信息（用于日志）
        """
        from src.utils.token_blacklist import token_blacklist

        try:
            import jwt
            from src.setting import settings
            from datetime import datetime

            payload = jwt.decode(
                token,
                getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
                algorithms=[getattr(settings, "JWT_ALGORITHM", "HS256")],
                options={"verify_exp": False}
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                expires_at = datetime.fromtimestamp(exp)
                token_blacklist.add_to_blacklist(jti, expires_at)
                logger.info(f"Added JTI {jti} to blacklist for {description}")
            else:
                logger.warning(f"Token for {description} has no JTI or exp field")
        except Exception as e:
            logger.error(f"Failed to blacklist {description}: {e}")

    async def revoke_session(self, session_id: int, user_id: int, db_session=None,
                             refresh_token: Optional[str] = None) -> bool:
        """
        异步撤销指定会话（远程注销设备）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（用于权限验证）
            db_session: 异步数据库会话（可选）
            
        Returns:
            是否成功撤销
        """
        from src.utils.database.unified_manager import db_manager
        from src.utils.token_blacklist import token_blacklist

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            from sqlalchemy import select
            query = select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id
            )
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return False

            # 将 access_token 加入黑名单
            if session.access_token:
                await self._blacklist_jwt_token(session.access_token, f"session {session_id}")

            # 将 refresh_token 加入黑名单（如果提供）
            if refresh_token:
                await self._blacklist_jwt_token(refresh_token, f"refresh token for session {session_id}")

            session.is_active = False
            await db_session.commit()

            logger.info(f"Revoked session {session_id} for user {user_id}")
            return True
        finally:
            if should_close:
                await db_session.close()

    async def revoke_all_sessions(self, user_id: int, exclude_current: Optional[int] = None, db_session=None) -> int:
        """
        撤销用户的所有会话（退出所有设备）
        
        Args:
            user_id: 用户ID
            exclude_current: 排除当前会话ID
            db_session: 异步数据库会话（可选）
            
        Returns:
            撤销的会话数量
        """
        from src.utils.database.unified_manager import db_manager
        from src.utils.token_blacklist import token_blacklist
        from sqlalchemy import select

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            # 先查询所有要撤销的会话
            query = select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )

            if exclude_current:
                query = query.where(UserSession.id != exclude_current)

            result = await db_session.execute(query)
            sessions = result.scalars().all()

            # 将所有 access_token 加入黑名单
            count = 0
            for session in sessions:
                if session.access_token:
                    await self._blacklist_jwt_token(session.access_token, f"session {session.id}")

                session.is_active = False
                count += 1

            await db_session.commit()

            logger.info(f"Revoked {count} sessions for user {user_id}")
            return count
        finally:
            if should_close:
                await db_session.close()

    async def update_last_activity(self, access_token: str, db_session=None) -> bool:
        """
        更新会话的最后活动时间
        
        Args:
            access_token: JWT access token
            
        Returns:
            是否成功更新
        """
        from src.utils.database.unified_manager import db_manager
        from sqlalchemy import select

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            query = select(UserSession).where(
                UserSession.access_token == access_token,
                UserSession.is_active == True
            )
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return False

            # 检查是否已过期
            if session.expires_at < datetime.now():
                session.is_active = False
                await db_session.commit()
                return False

            session.last_activity = datetime.now()
            await db_session.commit()
            return True
        finally:
            if should_close:
                await db_session.close()

    async def cleanup_expired_sessions(self, db_session=None) -> int:
        """
        清理过期的会话
        
        Returns:
            清理的会话数量
        """
        from src.utils.database.unified_manager import db_manager
        from sqlalchemy import update

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            query = update(UserSession).where(
                UserSession.expires_at < datetime.now(),
                UserSession.is_active == True
            ).values(is_active=False)

            result = await db_session.execute(query)
            count = result.rowcount
            await db_session.commit()

            logger.info(f"Cleaned up {count} expired sessions")
            return count
        finally:
            if should_close:
                await db_session.close()

    async def get_session_by_token(self, access_token: str, db_session=None) -> Optional[UserSession]:
        """
        根据令牌获取会话
        
        Args:
            access_token: JWT access token
            
        Returns:
            会话对象或None
        """
        from src.utils.database.unified_manager import db_manager
        from sqlalchemy import select

        should_close = False
        if db_session is None:
            db_session = await db_manager.get_session().__aenter__()
            should_close = True

        try:
            query = select(UserSession).where(
                UserSession.access_token == access_token,
                UserSession.is_active == True
            )
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return None

            # 检查是否已过期
            if session.expires_at < datetime.now():
                session.is_active = False
                await db_session.commit()
                return None

            return session
        finally:
            if should_close:
                await db_session.close()

    def _format_session(self, session: UserSession) -> Dict:
        """格式化会话数据"""
        # 解析设备信息
        device_name = "未知设备"
        browser = "未知浏览器"
        os_name = "未知系统"

        if session.device_info:
            # 简单的设备信息解析（实际应使用专门的库如 user-agents）
            ua = session.device_info

            # 检测操作系统
            if 'Windows' in ua:
                os_name = 'Windows'
            elif 'Macintosh' in ua or 'Mac OS' in ua:
                os_name = 'macOS'
            elif 'Linux' in ua:
                os_name = 'Linux'
            elif 'Android' in ua:
                os_name = 'Android'
            elif 'iPhone' in ua or 'iPad' in ua:
                os_name = 'iOS'

            # 检测浏览器
            if 'Chrome' in ua and 'Edg' not in ua:
                browser = 'Chrome'
            elif 'Firefox' in ua:
                browser = 'Firefox'
            elif 'Safari' in ua and 'Chrome' not in ua:
                browser = 'Safari'
            elif 'Edg' in ua:
                browser = 'Edge'
            elif 'MSIE' in ua or 'Trident' in ua:
                browser = 'Internet Explorer'

            device_name = f"{os_name} / {browser}"

        # 判断是否为当前设备
        is_current = False

        return {
            'id': session.id,
            'device_name': device_name,
            'device_info': session.device_info,
            'ip_address': session.ip_address,
            'location': session.location,
            'last_activity': session.last_activity.isoformat() if session.last_activity else None,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'is_current': is_current,
            'is_expired': session.expires_at < datetime.now() if session.expires_at else False
        }


# 全局实例
session_management_service = SessionManagementService()
