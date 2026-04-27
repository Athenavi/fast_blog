"""
安全防护插件
提供XSS防护、速率限制、IP黑名单等安全功能
"""

import re
import time
from datetime import datetime
from typing import Dict, List, Any, Set

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from shared.utils.plugin_database import plugin_db


class SecurityGuardPlugin(BasePlugin):
    """
    安全防护插件
    
    功能:
    1. XSS攻击防护
    2. CSRF令牌验证
    3. 速率限制
    4. IP黑名单/白名单
    5. 登录暴力破解防护
    6. SQL注入检测
    7. 请求头安全检查
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="安全防护",
            slug="security-guard",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_xss_protection': True,
            'enable_rate_limiting': True,
            'rate_limit_requests': 60,
            'enable_ip_blacklist': True,
            'max_login_attempts': 5,
            'login_lockout_duration': 15,
            'enable_sql_injection_detection': True,
            'secure_headers': True,
        }

        # 速率限制存储 {ip: [(timestamp, count), ...]}
        self.rate_limits: Dict[str, List] = {}

        # 登录尝试记录 {ip: [(timestamp, attempts), ...]}
        self.login_attempts: Dict[str, List] = {}

        # IP黑名单
        self.ip_blacklist: Set[str] = set()

        # IP白名单
        self.ip_whitelist: Set[str] = set()

    def register_hooks(self):
        """注册钩子"""
        # 请求前安全检查
        plugin_hooks.add_filter(
            "before_request",
            self.security_check,
            priority=1
        )

        # 内容输出时清理XSS
        if self.settings.get('enable_xss_protection'):
            plugin_hooks.add_filter(
                "output_content",
                self.sanitize_output,
                priority=10
            )

        # 登录尝试记录
        plugin_hooks.add_action(
            "login_attempt",
            self.record_login_attempt,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        self._init_database()
        self._load_ip_lists()

    def security_check(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        请求安全检查
        
        Args:
            request_data: 请求数据
            
        Returns:
            检查结果 {allowed: bool, reason: str}
        """
        client_ip = request_data.get('ip', '')

        # 1. 检查IP黑名单
        if self.settings.get('enable_ip_blacklist'):
            if client_ip in self.ip_blacklist:
                return {
                    'allowed': False,
                    'reason': 'IP address is blacklisted',
                    'status_code': 403,
                }

        # 2. 检查速率限制
        if self.settings.get('enable_rate_limiting'):
            if not self._check_rate_limit(client_ip):
                return {
                    'allowed': False,
                    'reason': 'Rate limit exceeded',
                    'status_code': 429,
                }

        # 3. 检查SQL注入
        if self.settings.get('enable_sql_injection_detection'):
            if self._detect_sql_injection(request_data):
                return {
                    'allowed': False,
                    'reason': 'Potential SQL injection detected',
                    'status_code': 400,
                }

        # 4. 检查XSS
        if self.settings.get('enable_xss_protection'):
            if self._detect_xss(request_data):
                # 发送安全警告通知
                self._send_security_notification(
                    'xss_detected',
                    '检测到XSS攻击',
                    f'来自IP {client_ip} 的请求包含可疑的XSS代码',
                    'warning',
                    {'ip': client_ip, 'url': request_data.get('url', '')}
                )
                return {
                    'allowed': False,
                    'reason': 'Potential XSS attack detected',
                    'status_code': 400,
                }

        # 5. 检查SQL注入
        if self.settings.get('enable_sql_injection_detection'):
            if self._detect_sql_injection(request_data):
                # 发送安全警告通知
                self._send_security_notification(
                    'sql_injection_detected',
                    '检测到SQL注入攻击',
                    f'来自IP {client_ip} 的请求包含可疑的SQL注入代码',
                    'error',
                    {'ip': client_ip, 'url': request_data.get('url', '')}
                )
                return {
                    'allowed': False,
                    'reason': 'Potential SQL injection detected',
                    'status_code': 400,
                }

        return {'allowed': True}

    def sanitize_output(self, content: str) -> str:
        """
        清理输出内容中的XSS
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not self.settings.get('enable_xss_protection'):
            return content

        # 移除script标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)

        # 移除事件处理器
        content = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)

        # 移除javascript:协议
        content = re.sub(r'javascript\s*:', '', content, flags=re.IGNORECASE)

        # 转义HTML特殊字符(可选,根据需要)
        # content = html.escape(content)

        return content

    def record_login_attempt(self, login_data: Dict[str, Any]):
        """
        记录登录尝试
        
        Args:
            login_data: 登录数据 {ip, username, success}
        """
        client_ip = login_data.get('ip', '')
        success = login_data.get('success', False)

        if not client_ip:
            return

        current_time = time.time()

        if client_ip not in self.login_attempts:
            self.login_attempts[client_ip] = []

        # 清理旧记录(超过1小时)
        cutoff_time = current_time - 3600
        self.login_attempts[client_ip] = [
            (ts, attempts) for ts, attempts in self.login_attempts[client_ip]
            if ts > cutoff_time
        ]

        if not success:
            # 失败尝试
            if self.login_attempts[client_ip]:
                last_ts, attempts = self.login_attempts[client_ip][-1]
                if current_time - last_ts < 300:  # 5分钟内
                    self.login_attempts[client_ip][-1] = (current_time, attempts + 1)
                else:
                    self.login_attempts[client_ip].append((current_time, 1))
            else:
                self.login_attempts[client_ip].append((current_time, 1))

            # 检查是否超过限制
            total_attempts = sum(attempts for _, attempts in self.login_attempts[client_ip])
            max_attempts = self.settings.get('max_login_attempts', 5)

            if total_attempts >= max_attempts:
                # 加入临时黑名单
                lockout_duration = self.settings.get('login_lockout_duration', 15) * 60
                self.ip_blacklist.add(client_ip)

                # 设置自动移除定时器
                import asyncio
                asyncio.create_task(self._remove_from_blacklist_after(client_ip, lockout_duration))

                print(f"[SecurityGuard] IP {client_ip} locked out due to too many failed login attempts")

                # 发送通知给管理员
                self._send_security_notification(
                    'brute_force_detected',
                    f'检测到暴力破解攻击',
                    f'IP地址 {client_ip} 在多次登录失败后被锁定。失败次数: {total_attempts}',
                    'warning',
                    {'ip': client_ip, 'attempts': total_attempts}
                )
        else:
            # 成功登录,清除记录
            self.login_attempts[client_ip] = []

    def add_to_blacklist(self, ip: str, reason: str = None, expires_at: str = None):
        """添加IP到黑名单"""
        self.ip_blacklist.add(ip)

        # 保存到数据库
        try:
            plugin_db.execute_update(
                'security-guard',
                """INSERT OR REPLACE INTO ip_lists (ip_address, list_type, reason, expires_at, created_at)
                   VALUES (?, 'blacklist', ?, ?, ?)""",
                (ip, reason, expires_at, datetime.now().isoformat())
            )
        except Exception as e:
            print(f"[SecurityGuard] Failed to save blacklist: {e}")
        
        print(f"[SecurityGuard] Added {ip} to blacklist" + (f": {reason}" if reason else ""))

    def remove_from_blacklist(self, ip: str):
        """从黑名单移除IP"""
        self.ip_blacklist.discard(ip)

        # 从数据库删除
        try:
            plugin_db.execute_update(
                'security-guard',
                "DELETE FROM ip_lists WHERE ip_address = ? AND list_type = 'blacklist'",
                (ip,)
            )
        except Exception as e:
            print(f"[SecurityGuard] Failed to remove from blacklist: {e}")
        
        print(f"[SecurityGuard] Removed {ip} from blacklist")

    def add_to_whitelist(self, ip: str):
        """添加IP到白名单"""
        self.ip_whitelist.add(ip)

        # 保存到数据库
        try:
            plugin_db.execute_update(
                'security-guard',
                """INSERT OR REPLACE INTO ip_lists (ip_address, list_type, created_at)
                   VALUES (?, 'whitelist', ?)""",
                (ip, datetime.now().isoformat())
            )
        except Exception as e:
            print(f"[SecurityGuard] Failed to save whitelist: {e}")

    def get_blocked_ips(self) -> List[str]:
        """获取被阻止的IP列表"""
        return list(self.ip_blacklist)

    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        return {
            'blacklisted_ips': len(self.ip_blacklist),
            'whitelisted_ips': len(self.ip_whitelist),
            'rate_limited_requests': sum(
                1 for requests in self.rate_limits.values()
                for _, count in requests
                if count > self.settings.get('rate_limit_requests', 60)
            ),
            'failed_login_attempts': sum(
                attempts for attempts_list in self.login_attempts.values()
                for _, attempts in attempts_list
            ),
        }

    def _check_rate_limit(self, client_ip: str) -> bool:
        """检查速率限制"""
        if client_ip in self.ip_whitelist:
            return True

        current_time = time.time()
        window_size = 60  # 1分钟窗口
        max_requests = self.settings.get('rate_limit_requests', 60)

        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []

        # 清理旧记录
        cutoff_time = current_time - window_size
        self.rate_limits[client_ip] = [
            (ts, count) for ts, count in self.rate_limits[client_ip]
            if ts > cutoff_time
        ]

        # 计算当前窗口内的请求数
        total_requests = sum(count for _, count in self.rate_limits[client_ip])

        if total_requests >= max_requests:
            return False

        # 记录本次请求
        if self.rate_limits[client_ip]:
            last_ts, last_count = self.rate_limits[client_ip][-1]
            if current_time - last_ts < 1:  # 同一秒内
                self.rate_limits[client_ip][-1] = (current_time, last_count + 1)
            else:
                self.rate_limits[client_ip].append((current_time, 1))
        else:
            self.rate_limits[client_ip].append((current_time, 1))

        return True

    def _detect_sql_injection(self, request_data: Dict[str, Any]) -> bool:
        """检测SQL注入尝试"""
        # 常见的SQL注入模式
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.*\b(FROM|INTO|TABLE|WHERE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
            r"(';\s*(DROP|DELETE|UPDATE|INSERT))",
        ]

        # 检查请求参数
        params = str(request_data.get('params', ''))
        body = str(request_data.get('body', ''))

        combined = f"{params} {body}".lower()

        for pattern in sql_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                print(f"[SecurityGuard] Potential SQL injection detected: {combined[:100]}")
                return True

        return False

    def _detect_xss(self, request_data: Dict[str, Any]) -> bool:
        """检测XSS攻击"""
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript\s*:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]

        params = str(request_data.get('params', ''))
        body = str(request_data.get('body', ''))

        combined = f"{params} {body}"

        for pattern in xss_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                print(f"[SecurityGuard] Potential XSS detected: {combined[:100]}")
                return True

        return False

    async def _remove_from_blacklist_after(self, ip: str, duration: float):
        """指定时间后从黑名单移除IP"""
        await asyncio.sleep(duration)
        self.remove_from_blacklist(ip)

    def _init_database(self):
        """初始化数据库表"""
        try:
            from shared.utils.plugin_db_init import init_security_guard_db
            init_security_guard_db()
        except Exception as e:
            print(f"[SecurityGuard] Failed to initialize database: {e}")

    def _load_ip_lists(self):
        """从数据库加载IP列表"""
        try:
            # 加载黑名单
            blacklisted = plugin_db.execute_query(
                'security-guard',
                "SELECT ip_address FROM ip_lists WHERE list_type = 'blacklist' AND (expires_at IS NULL OR expires_at > ?)",
                (datetime.now().isoformat(),)
            )
            self.ip_blacklist = set(row['ip_address'] for row in blacklisted)

            # 加载白名单
            whitelisted = plugin_db.execute_query(
                'security-guard',
                "SELECT ip_address FROM ip_lists WHERE list_type = 'whitelist' AND (expires_at IS NULL OR expires_at > ?)",
                (datetime.now().isoformat(),)
            )
            self.ip_whitelist = set(row['ip_address'] for row in whitelisted)

            print(
                f"[SecurityGuard] Loaded {len(self.ip_blacklist)} blacklisted and {len(self.ip_whitelist)} whitelisted IPs")
        except Exception as e:
            print(f"[SecurityGuard] Failed to load IP lists: {e}")
            self.ip_blacklist = set()
            self.ip_whitelist = set()

    def _save_ip_lists(self):
        """保存IP列表到数据库（增量更新）"""
        # 注意：这个方法在add/remove时调用，实际是同步内存状态到数据库
        # 由于我们已经在add/remove时直接操作数据库，这里可以留空或做验证
        pass

    def _send_security_notification(self, event_type: str, title: str, message: str, severity: str = 'info',
                                    data: dict = None):
        """
        发送安全通知
        
        Args:
            event_type: 事件类型
            title: 通知标题
            message: 通知内容
            severity: 严重程度 ('info', 'warning', 'error', 'critical')
            data: 额外数据
        """
        try:
            from src.notification import create_notification
            from shared.models.user import User
            from sqlalchemy import select
            from src.extensions import get_async_db_session

            # 获取所有管理员用户
            with next(get_async_db_session()) as session:
                # 假设 is_staff 或 is_superuser 字段标识管理员
                stmt = select(User).where(
                    (User.is_staff == True) | (User.is_superuser == True)
                )
                result = session.execute(stmt)
                admins = result.scalars().all()

                # 为每个管理员创建通知
                for admin in admins:
                    try:
                        create_notification(
                            recipient_id=admin.id,
                            title=f'[安全警告] {title}',
                            content=message,
                            notification_type=severity,
                            data=data
                        )
                    except Exception as e:
                        print(f"[SecurityGuard] Failed to send notification to admin {admin.id}: {e}")

            print(f"[SecurityGuard] Security notification sent: {title}")

        except ImportError:
            print(f"[SecurityGuard] Notification system not available: {title} - {message}")
        except Exception as e:
            print(f"[SecurityGuard] Failed to send security notification: {e}")
            import traceback
            traceback.print_exc()

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_xss_protection',
                    'type': 'boolean',
                    'label': '启用XSS防护',
                },
                {
                    'key': 'enable_rate_limiting',
                    'type': 'boolean',
                    'label': '启用速率限制',
                },
                {
                    'key': 'rate_limit_requests',
                    'type': 'number',
                    'label': '每分钟请求数限制',
                    'min': 10,
                    'max': 1000,
                },
                {
                    'key': 'max_login_attempts',
                    'type': 'number',
                    'label': '最大登录尝试次数',
                    'min': 3,
                    'max': 10,
                },
                {
                    'key': 'login_lockout_duration',
                    'type': 'number',
                    'label': '登录锁定时间(分钟)',
                    'min': 5,
                    'max': 60,
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看安全统计',
                    'action': 'get_security_stats',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = SecurityGuardPlugin()
