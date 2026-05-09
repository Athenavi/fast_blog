"""
登录安全服务
提供异地登录检测、频繁失败锁定、设备指纹识别等功能
"""

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class LoginSecurityService:
    """登录安全服务"""

    def __init__(self):
        # 登录失败记录 {user_id: [(timestamp, ip_address), ...]}
        self._login_failures = defaultdict(list)

        # 用户锁定状态 {user_id: lock_info}
        self._user_locks = {}

        # 登录历史 {user_id: [login_record, ...]}
        self._login_history = defaultdict(list)

        # 配置参数
        self.max_failures = 5  # 最大失败次数
        self.lock_duration_minutes = 30  # 锁定时长(分钟)
        self.failure_window_minutes = 15  # 失败时间窗口(分钟)

    def record_login_failure(self, user_id: int, ip_address: str,
                             user_agent: str = '') -> Dict:
        """
        记录登录失败
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: User-Agent
            
        Returns:
            检查结果(是否被锁定)
        """
        now = datetime.now()

        # 记录失败
        self._login_failures[user_id].append({
            'timestamp': now,
            'ip_address': ip_address,
            'user_agent': user_agent,
        })

        # 清理旧记录(超出时间窗口的)
        cutoff = now - timedelta(minutes=self.failure_window_minutes)
        self._login_failures[user_id] = [
            f for f in self._login_failures[user_id]
            if f['timestamp'] > cutoff
        ]

        # 检查失败次数
        recent_failures = len(self._login_failures[user_id])

        if recent_failures >= self.max_failures:
            # 锁定账户
            lock_until = now + timedelta(minutes=self.lock_duration_minutes)
            self._user_locks[user_id] = {
                'locked_at': now,
                'lock_until': lock_until,
                'failure_count': recent_failures,
                'ip_address': ip_address,
            }

            logger.warning(f"User {user_id} locked due to {recent_failures} failed login attempts")

            return {
                'is_locked': True,
                'lock_until': lock_until.isoformat(),
                'remaining_minutes': self.lock_duration_minutes,
                'failure_count': recent_failures,
            }

        return {
            'is_locked': False,
            'failure_count': recent_failures,
            'remaining_attempts': self.max_failures - recent_failures,
        }

    def check_user_locked(self, user_id: int) -> Dict:
        """
        检查用户是否被锁定
        
        Args:
            user_id: 用户ID
            
        Returns:
            锁定状态
        """
        lock_info = self._user_locks.get(user_id)

        if not lock_info:
            return {'is_locked': False}

        now = datetime.now()

        # 检查是否已过期
        if now >= lock_info['lock_until']:
            # 解锁并清除失败记录
            del self._user_locks[user_id]
            self._login_failures[user_id] = []

            return {'is_locked': False}

        # 仍然锁定
        remaining_seconds = (lock_info['lock_until'] - now).total_seconds()
        remaining_minutes = int(remaining_seconds / 60)

        return {
            'is_locked': True,
            'lock_until': lock_info['lock_until'].isoformat(),
            'remaining_minutes': remaining_minutes,
            'failure_count': lock_info['failure_count'],
        }

    def unlock_user(self, user_id: int) -> bool:
        """
        手动解锁用户(管理员操作)
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        if user_id in self._user_locks:
            del self._user_locks[user_id]
            self._login_failures[user_id] = []

            logger.info(f"User {user_id} manually unlocked by admin")
            return True

        return False

    def record_login_success(self, user_id: int, ip_address: str,
                             user_agent: str = '', device_info: Dict = None) -> Dict:
        """
        记录登录成功
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: User-Agent
            device_info: 设备信息
            
        Returns:
            安全检查结果
        """
        now = datetime.now()

        # 生成设备指纹
        device_fingerprint = self._generate_device_fingerprint(device_info or {}, user_agent)

        # 记录登录历史
        login_record = {
            'timestamp': now,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_fingerprint': device_fingerprint,
            'device_info': device_info or {},
            'success': True,
        }

        self._login_history[user_id].append(login_record)

        # 清除失败记录
        self._login_failures[user_id] = []

        # 检测异常
        alerts = self._detect_anomalies(user_id, login_record)

        return {
            'success': True,
            'alerts': alerts,
            'device_fingerprint': device_fingerprint,
        }

    def _detect_anomalies(self, user_id: int, current_login: Dict) -> List[Dict]:
        """
        检测登录异常
        
        Args:
            user_id: 用户ID
            current_login: 当前登录记录
            
        Returns:
            异常告警列表
        """
        alerts = []
        history = self._login_history.get(user_id, [])

        if not history:
            return alerts

        # 获取上次登录
        last_login = history[-1] if len(history) > 1 else None

        if not last_login:
            return alerts

        # 1. 检测异地登录(IP变化)
        if current_login['ip_address'] != last_login['ip_address']:
            alerts.append({
                'type': 'new_location',
                'severity': 'warning',
                'message': f'检测到新的登录地点',
                'current_ip': current_login['ip_address'],
                'last_ip': last_login['ip_address'],
            })

        # 2. 检测新设备
        if current_login['device_fingerprint'] != last_login['device_fingerprint']:
            alerts.append({
                'type': 'new_device',
                'severity': 'info',
                'message': '检测到新设备登录',
                'current_device': current_login.get('device_info', {}),
            })

        # 3. 检测异常时间(凌晨登录)
        current_hour = current_login['timestamp'].hour
        if current_hour >= 0 and current_hour < 5:
            alerts.append({
                'type': 'unusual_time',
                'severity': 'info',
                'message': '检测到非正常时间登录',
                'login_time': current_login['timestamp'].isoformat(),
            })

        # 4. 检测频繁登录(1小时内多次)
        one_hour_ago = current_login['timestamp'] - timedelta(hours=1)
        recent_logins = [
            l for l in history
            if l['timestamp'] > one_hour_ago and l.get('success', False)
        ]

        if len(recent_logins) >= 5:
            alerts.append({
                'type': 'frequent_login',
                'severity': 'warning',
                'message': f'1小时内登录{len(recent_logins)}次',
                'login_count': len(recent_logins),
            })

        return alerts

    def get_login_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        获取用户登录历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量
            
        Returns:
            登录历史记录
        """
        history = self._login_history.get(user_id, [])

        # 返回最近的记录
        recent_history = history[-limit:]

        return [
            {
                'timestamp': record['timestamp'].isoformat(),
                'ip_address': record['ip_address'],
                'user_agent': record['user_agent'],
                'device_fingerprint': record['device_fingerprint'],
                'device_info': record.get('device_info', {}),
                'success': record.get('success', False),
            }
            for record in reversed(recent_history)
        ]

    def get_security_stats(self, user_id: int) -> Dict:
        """
        获取用户安全统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计数据
        """
        history = self._login_history.get(user_id, [])
        failures = self._login_failures.get(user_id, [])

        # 统计不同IP数量
        unique_ips = set(r['ip_address'] for r in history if r.get('success'))

        # 统计不同设备数量
        unique_devices = set(r['device_fingerprint'] for r in history if r.get('success'))

        # 最近7天登录次数
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_logins = [
            r for r in history
            if r['timestamp'] > seven_days_ago and r.get('success')
        ]
        
        return {
            'total_logins': len([r for r in history if r.get('success')]),
            'total_failures': len([r for r in history if not r.get('success')]),
            'unique_ips': len(unique_ips),
            'unique_devices': len(unique_devices),
            'recent_7days_logins': len(recent_logins),
            'current_failures': len(failures),
            'is_locked': user_id in self._user_locks,
        }

    def _generate_device_fingerprint(self, device_info: Dict,
                                     user_agent: str = '') -> str:
        """
        生成设备指纹
        
        Args:
            device_info: 设备信息
            user_agent: User-Agent
            
        Returns:
            设备指纹哈希
        """
        data = f"{device_info}:{user_agent}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def get_locked_users(self) -> List[Dict]:
        """
        获取所有被锁定的用户(管理员)
        
        Returns:
            锁定用户列表
        """
        locked_users = []
        now = datetime.now()

        for user_id, lock_info in self._user_locks.items():
            if now < lock_info['lock_until']:
                remaining_seconds = (lock_info['lock_until'] - now).total_seconds()
                locked_users.append({
                    'user_id': user_id,
                    'locked_at': lock_info['locked_at'].isoformat(),
                    'lock_until': lock_info['lock_until'].isoformat(),
                    'remaining_minutes': int(remaining_seconds / 60),
                    'failure_count': lock_info['failure_count'],
                    'ip_address': lock_info['ip_address'],
                })

        return locked_users


# 全局实例
login_security_service = LoginSecurityService()
