"""
安全增强插件 (Security Pro)
提供登录失败锁定、IP白名单/黑名单、安全日志审计和定期安全扫描功能
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class SecurityProPlugin(BasePlugin):
    """
    安全增强插件
    
    功能:
    1. 登录失败锁定 - 防止暴力破解
    2. IP白名单/黑名单 - 访问控制
    3. 安全日志审计 - 记录所有安全事件
    4. 定期安全扫描 - 检测潜在漏洞
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="安全增强",
            slug="security-pro",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_login_lockout': True,
            'max_login_attempts': 5,
            'lockout_duration': 30,
            'enable_ip_whitelist': False,
            'ip_whitelist': '',
            'ip_blacklist': '',
            'enable_security_scan': True,
            'scan_frequency': 'weekly',
            'enable_audit_log': True,
        }

        # 登录尝试记录 {username: [(timestamp, ip), ...]}
        self.login_attempts: Dict[str, List[tuple]] = defaultdict(list)

        # 被锁定的用户 {username: lockout_until}
        self.locked_users: Dict[str, datetime] = {}

        # 安全日志
        self.security_logs: List[Dict[str, Any]] = []

        # 安全扫描结果
        self.scan_results: List[Dict[str, Any]] = []

    def register_hooks(self):
        """注册钩子"""
        # 登录前检查
        plugin_hooks.add_filter(
            "pre_login_check",
            self.check_login_attempt,
            priority=5
        )

        # 登录失败记录
        plugin_hooks.add_action(
            "login_failed",
            self.record_failed_login,
            priority=10
        )

        # 登录成功清除记录
        plugin_hooks.add_action(
            "login_success",
            self.clear_login_attempts,
            priority=10
        )

        # 请求前检查IP
        plugin_hooks.add_filter(
            "request_pre_check",
            self.check_ip_access,
            priority=5
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[SecurityPro] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[SecurityPro] Plugin deactivated")

    def check_login_attempt(self, login_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查登录尝试
        
        Args:
            login_data: {username, ip}
            
        Returns:
            检查结果 {allowed: bool, message: str}
        """
        if not self.settings.get('enable_login_lockout'):
            return {'allowed': True}

        username = login_data.get('username', '')

        # 检查是否被锁定
        if username in self.locked_users:
            lockout_until = self.locked_users[username]
            if datetime.now() < lockout_until:
                remaining_minutes = int((lockout_until - datetime.now()).total_seconds() / 60)
                self._log_security_event('login_blocked', {
                    'username': username,
                    'ip': login_data.get('ip'),
                    'reason': 'Account locked',
                })
                return {
                    'allowed': False,
                    'message': f'Account locked. Try again in {remaining_minutes} minutes.',
                }
            else:
                # 锁定已过期，清除
                del self.locked_users[username]

        return {'allowed': True}

    def record_failed_login(self, login_data: Dict[str, Any]):
        """
        记录失败的登录尝试
        
        Args:
            login_data: {username, ip}
        """
        if not self.settings.get('enable_login_lockout'):
            return

        username = login_data.get('username', '')
        ip = login_data.get('ip', '')

        # 记录尝试
        self.login_attempts[username].append((datetime.now(), ip))

        # 检查是否超过最大尝试次数
        max_attempts = self.settings.get('max_login_attempts', 5)
        recent_attempts = [
            attempt for attempt in self.login_attempts[username]
            if (datetime.now() - attempt[0]).total_seconds() < 3600  # 1小时内
        ]

        if len(recent_attempts) >= max_attempts:
            # 锁定账户
            lockout_duration = self.settings.get('lockout_duration', 30)
            lockout_until = datetime.now() + timedelta(minutes=lockout_duration)
            self.locked_users[username] = lockout_until

            self._log_security_event('account_locked', {
                'username': username,
                'ip': ip,
                'attempts': len(recent_attempts),
                'lockout_until': lockout_until.isoformat(),
            })

            print(f"[SecurityPro] Account locked: {username} until {lockout_until}")

        self._log_security_event('login_failed', {
            'username': username,
            'ip': ip,
            'attempt_count': len(recent_attempts),
        })

    def clear_login_attempts(self, login_data: Dict[str, Any]):
        """
        登录成功后清除尝试记录
        
        Args:
            login_data: {username}
        """
        username = login_data.get('username', '')
        if username in self.login_attempts:
            del self.login_attempts[username]

        self._log_security_event('login_success', {
            'username': username,
            'ip': login_data.get('ip'),
        })

    def check_ip_access(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查IP访问权限
        
        Args:
            request_data: {ip, path}
            
        Returns:
            检查结果 {allowed: bool, message: str}
        """
        ip = request_data.get('ip', '')

        # 检查黑名单
        blacklist = self._parse_ip_list(self.settings.get('ip_blacklist', ''))
        if ip in blacklist:
            self._log_security_event('ip_blocked', {
                'ip': ip,
                'path': request_data.get('path'),
                'reason': 'Blacklisted',
            })
            return {
                'allowed': False,
                'message': 'Access denied from your IP address.',
            }

        # 检查白名单(如果启用)
        if self.settings.get('enable_ip_whitelist'):
            whitelist = self._parse_ip_list(self.settings.get('ip_whitelist', ''))
            if whitelist and ip not in whitelist:
                self._log_security_event('ip_blocked', {
                    'ip': ip,
                    'path': request_data.get('path'),
                    'reason': 'Not in whitelist',
                })
                return {
                    'allowed': False,
                    'message': 'Access denied. Your IP is not authorized.',
                }

        return {'allowed': True}

    def run_security_scan(self) -> Dict[str, Any]:
        """
        执行安全扫描
        
        Returns:
            扫描结果
        """
        scan_result = {
            'scan_id': f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'status': 'completed',
            'issues': [],
            'warnings': [],
            'passed_checks': [],
        }

        # 1. 检查弱密码
        weak_password_users = self._check_weak_passwords()
        if weak_password_users:
            scan_result['issues'].append({
                'severity': 'high',
                'type': 'weak_passwords',
                'description': f'{len(weak_password_users)} users have weak passwords',
                'affected_users': weak_password_users[:10],  # 只返回前10个
            })
        else:
            scan_result['passed_checks'].append('password_strength')

        # 2. 检查过期的会话
        expired_sessions = self._check_expired_sessions()
        if expired_sessions > 0:
            scan_result['warnings'].append({
                'type': 'expired_sessions',
                'description': f'{expired_sessions} expired sessions found',
            })
        else:
            scan_result['passed_checks'].append('session_management')

        # 3. 检查文件权限
        permission_issues = self._check_file_permissions()
        if permission_issues:
            scan_result['issues'].extend(permission_issues)
        else:
            scan_result['passed_checks'].append('file_permissions')

        # 4. 检查可疑活动
        suspicious_activities = self._detect_suspicious_activity()
        if suspicious_activities:
            scan_result['warnings'].extend(suspicious_activities)
        else:
            scan_result['passed_checks'].append('activity_monitoring')

        # 保存扫描结果
        self.scan_results.append(scan_result)

        self._log_security_event('security_scan_completed', {
            'scan_id': scan_result['scan_id'],
            'issues_count': len(scan_result['issues']),
            'warnings_count': len(scan_result['warnings']),
        })

        print(
            f"[SecurityPro] Security scan completed: {len(scan_result['issues'])} issues, {len(scan_result['warnings'])} warnings")
        return scan_result

    def get_security_logs(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取安全日志
        
        Args:
            limit: 返回数量限制
            event_type: 事件类型过滤
            
        Returns:
            安全日志列表
        """
        filtered = self.security_logs

        if event_type:
            filtered = [log for log in filtered if log.get('event_type') == event_type]

        # 按时间倒序
        sorted_logs = sorted(
            filtered,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )

        return sorted_logs[:limit]

    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        total_events = len(self.security_logs)
        failed_logins = len([log for log in self.security_logs if log.get('event_type') == 'login_failed'])
        blocked_ips = len([log for log in self.security_logs if log.get('event_type') == 'ip_blocked'])
        locked_accounts = len(self.locked_users)

        # 最近7天的趋势
        last_7_days = datetime.now() - timedelta(days=7)
        recent_events = [
            log for log in self.security_logs
            if datetime.fromisoformat(log.get('timestamp', datetime.now().isoformat())) > last_7_days
        ]

        return {
            'total_events': total_events,
            'failed_logins_24h': failed_logins,
            'blocked_ips_24h': blocked_ips,
            'locked_accounts': locked_accounts,
            'recent_events_7d': len(recent_events),
            'last_scan': self.scan_results[-1] if self.scan_results else None,
        }

    def add_to_blacklist(self, ip: str, reason: str = ''):
        """添加到黑名单"""
        current_blacklist = self.settings.get('ip_blacklist', '')
        ips = [ip.strip() for ip in current_blacklist.split('\n') if ip.strip()]

        if ip not in ips:
            ips.append(ip)
            self.settings['ip_blacklist'] = '\n'.join(ips)

            self._log_security_event('ip_blacklisted', {
                'ip': ip,
                'reason': reason,
            })
            print(f"[SecurityPro] IP added to blacklist: {ip}")

    def remove_from_blacklist(self, ip: str):
        """从黑名单移除"""
        current_blacklist = self.settings.get('ip_blacklist', '')
        ips = [ip.strip() for ip in current_blacklist.split('\n') if ip.strip()]

        if ip in ips:
            ips.remove(ip)
            self.settings['ip_blacklist'] = '\n'.join(ips)
            print(f"[SecurityPro] IP removed from blacklist: {ip}")

    def _parse_ip_list(self, ip_string: str) -> List[str]:
        """解析IP列表字符串"""
        if not ip_string:
            return []
        return [ip.strip() for ip in ip_string.split('\n') if ip.strip()]

    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """记录安全事件"""
        if not self.settings.get('enable_audit_log'):
            return

        log_entry = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'details': details,
        }

        self.security_logs.append(log_entry)

        # 限制日志数量(保留最近10000条)
        if len(self.security_logs) > 10000:
            self.security_logs = self.security_logs[-10000:]

    def _check_weak_passwords(self) -> List[str]:
        """检查弱密码(模拟)"""
        # 实际应集成密码强度检查
        return []

    def _check_expired_sessions(self) -> int:
        """检查过期会话(模拟)"""
        return 0

    def _check_file_permissions(self) -> List[Dict[str, Any]]:
        """检查文件权限(模拟)"""
        return []

    def _detect_suspicious_activity(self) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        warnings = []

        # 检查频繁的登录失败
        for username, attempts in self.login_attempts.items():
            recent_attempts = [
                attempt for attempt in attempts
                if (datetime.now() - attempt[0]).total_seconds() < 300  # 5分钟内
            ]
            if len(recent_attempts) > 10:
                warnings.append({
                    'type': 'brute_force_detected',
                    'description': f'Possible brute force attack on user: {username}',
                    'attempts': len(recent_attempts),
                })

        return warnings

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_login_lockout',
                    'type': 'boolean',
                    'label': '启用登录失败锁定',
                },
                {
                    'key': 'max_login_attempts',
                    'type': 'number',
                    'label': '最大登录尝试次数',
                    'min': 1,
                    'max': 10,
                },
                {
                    'key': 'lockout_duration',
                    'type': 'number',
                    'label': '锁定时长(分钟)',
                    'min': 5,
                    'max': 1440,
                },
                {
                    'key': 'enable_ip_whitelist',
                    'type': 'boolean',
                    'label': '启用IP白名单',
                },
                {
                    'key': 'ip_whitelist',
                    'type': 'textarea',
                    'label': 'IP白名单(每行一个)',
                },
                {
                    'key': 'ip_blacklist',
                    'type': 'textarea',
                    'label': 'IP黑名单(每行一个)',
                },
                {
                    'key': 'enable_security_scan',
                    'type': 'boolean',
                    'label': '启用定期安全扫描',
                },
                {
                    'key': 'scan_frequency',
                    'type': 'select',
                    'label': '扫描频率',
                    'options': [
                        {'value': 'daily', 'label': '每天'},
                        {'value': 'weekly', 'label': '每周'},
                        {'value': 'monthly', 'label': '每月'},
                    ],
                },
                {
                    'key': 'enable_audit_log',
                    'type': 'boolean',
                    'label': '启用审计日志',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '立即执行安全扫描',
                    'action': 'run_security_scan',
                    'variant': 'default',
                },
                {
                    'type': 'button',
                    'label': '查看安全日志',
                    'action': 'view_logs',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = SecurityProPlugin()
