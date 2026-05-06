"""
用户会话管理服务
提供会话管理、设备管理等功能
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from shared.models.user_session import UserSession
from src.extensions import db

logger = logging.getLogger(__name__)


class SessionManagementService:
    """会话管理服务"""

    def create_session(
            self,
            user_id: int,
            session_token: str,
            device_info: Optional[str] = None,
            ip_address: Optional[str] = None,
            location: Optional[str] = None,
            expires_hours: int = 720  # 默认30天
    ) -> UserSession:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            session_token: 会话令牌
            device_info: 设备信息
            ip_address: IP地址
            location: 地理位置
            expires_hours: 过期时间（小时）
            
        Returns:
            创建的会话对象
        """
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            device_info=device_info,
            ip_address=ip_address,
            location=location,
            is_active=True,
            last_activity=datetime.utcnow(),
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )

        db.session.add(session)
        db.session.commit()

        logger.info(f"Created new session for user {user_id}")
        return session

    def get_user_sessions(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            active_only: 只返回活跃会话
            
        Returns:
            会话列表
        """
        query = UserSession.query.filter_by(user_id=user_id)

        if active_only:
            query = query.filter_by(is_active=True)
            # 过滤已过期的会话
            query = query.filter(UserSession.expires_at > datetime.utcnow())

        sessions = query.order_by(UserSession.last_activity.desc()).all()

        return [self._format_session(s) for s in sessions]

    def revoke_session(self, session_id: int, user_id: int) -> bool:
        """
        撤销指定会话（远程注销设备）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否成功撤销
        """
        session = UserSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()

        if not session:
            return False

        session.is_active = False
        db.session.commit()

        logger.info(f"Revoked session {session_id} for user {user_id}")
        return True

    def revoke_all_sessions(self, user_id: int, exclude_current: Optional[int] = None) -> int:
        """
        撤销用户的所有会话（退出所有设备）
        
        Args:
            user_id: 用户ID
            exclude_current: 排除当前会话ID
            
        Returns:
            撤销的会话数量
        """
        query = UserSession.query.filter_by(
            user_id=user_id,
            is_active=True
        )

        if exclude_current:
            query = query.filter(UserSession.id != exclude_current)

        count = query.update({'is_active': False})
        db.session.commit()

        logger.info(f"Revoked {count} sessions for user {user_id}")
        return count

    def update_last_activity(self, session_token: str) -> bool:
        """
        更新会话的最后活动时间
        
        Args:
            session_token: 会话令牌
            
        Returns:
            是否成功更新
        """
        session = UserSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()

        if not session:
            return False

        # 检查是否已过期
        if session.expires_at < datetime.utcnow():
            session.is_active = False
            db.session.commit()
            return False

        session.last_activity = datetime.utcnow()
        db.session.commit()
        return True

    def cleanup_expired_sessions(self) -> int:
        """
        清理过期的会话
        
        Returns:
            清理的会话数量
        """
        count = UserSession.query.filter(
            UserSession.expires_at < datetime.utcnow(),
            UserSession.is_active == True
        ).update({'is_active': False})

        db.session.commit()
        logger.info(f"Cleaned up {count} expired sessions")
        return count

    def get_session_by_token(self, session_token: str) -> Optional[UserSession]:
        """
        根据令牌获取会话
        
        Args:
            session_token: 会话令牌
            
        Returns:
            会话对象或None
        """
        session = UserSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()

        if not session:
            return None

        # 检查是否已过期
        if session.expires_at < datetime.utcnow():
            session.is_active = False
            db.session.commit()
            return None

        return session

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
            'is_expired': session.expires_at < datetime.utcnow() if session.expires_at else False
        }


# 全局实例
session_management_service = SessionManagementService()
