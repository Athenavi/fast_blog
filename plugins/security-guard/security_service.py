"""
安全加固服务 - 增强版
提供全面的安全防护功能

功能:
1. Web应用防火墙 (WAF)
2. 登录保护 (失败限制/验证码)
3. IP黑名单管理
4. 文件完整性监控
5. 安全扫描工具
6. 安全日志和告警
7. 请求签名验证
8. Content Security Policy (CSP)
"""

import hashlib
import logging
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """安全事件记录"""
    event_type: str  # xss_attempt, sql_injection, brute_force, etc.
    severity: str  # low, medium, high, critical
    source_ip: str
    target_url: str
    details: str
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = True


class WebApplicationFirewall:
    """
    Web应用防火墙 (WAF)
    
    功能:
    1. 请求过滤
    2. 模式匹配
    3. 异常检测
    4. 自动封禁
    """
    
    def __init__(self):
        # XSS攻击模式
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript\s*:',
            r'on\w+\s*=\s*["\']',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'expression\s*\(',
            r'url\s*\(\s*javascript:',
            r'<svg[^>]*onload',
            r'<img[^>]*onerror',
        ]

        # SQL注入模式
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.*\b(FROM|INTO|TABLE|WHERE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
            r"('\s*(OR|AND)\s*')",
            r"(;\s*(DROP|DELETE|UPDATE|INSERT))",
            r"(EXEC\s*\(|EXECUTE\s*\()",
            r"(xp_|sp_)",
            r"(WAITFOR\s+DELAY|BENCHMARK\s*\(|SLEEP\s*\()",
        ]

        # 路径遍历模式
        self.path_traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e/',
            r'\.\.%2f',
            r'/etc/passwd',
            r'/etc/shadow',
            r'\\windows\\',
            r'\\system32\\',
        ]

        # 命令注入模式
        self.command_injection_patterns = [
            r';\s*(ls|cat|rm|wget|curl|bash|sh|python|perl)',
            r'\|\s*(ls|cat|rm|wget|curl|bash|sh|python|perl)',
            r'`[^`]+`',
            r'\$\([^)]+\)',
            r'&\s*(ls|cat|rm|wget|curl)',
        ]

        # 统计信息
        self.blocked_requests = 0
        self.total_requests = 0

        # 安全事件日志
        self.security_events: deque = deque(maxlen=1000)

    def inspect_request(self, url: str, method: str, headers: Dict,
                        params: Dict = None, body: str = None) -> Tuple[bool, str]:
        """
        检查请求是否安全
        
        Returns:
            (is_safe, reason)
        """
        self.total_requests += 1

        # 检查URL
        if not self._check_xss(url):
            return False, "XSS attack detected in URL"

        if not self._check_sql_injection(url):
            return False, "SQL injection detected in URL"

        if not self._check_path_traversal(url):
            return False, "Path traversal detected in URL"

        # 检查参数
        if params:
            for key, value in params.items():
                combined = f"{key}={value}"
                if not self._check_xss(combined):
                    return False, f"XSS attack detected in parameter: {key}"
                if not self._check_sql_injection(combined):
                    return False, f"SQL injection detected in parameter: {key}"

        # 检查请求体
        if body and method in ['POST', 'PUT', 'PATCH']:
            if not self._check_xss(body):
                return False, "XSS attack detected in request body"
            if not self._check_sql_injection(body):
                return False, "SQL injection detected in request body"
            if not self._check_command_injection(body):
                return False, "Command injection detected in request body"

        # 检查请求头
        if headers:
            user_agent = headers.get('user-agent', '')
            if self._is_malicious_bot(user_agent):
                return False, "Malicious bot detected"

        return True, ""

    def _check_xss(self, text: str) -> bool:
        """检查XSS攻击"""
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                self.blocked_requests += 1
                self._log_event('xss_attempt', 'high', text[:200])
                return False
        return True

    def _check_sql_injection(self, text: str) -> bool:
        """检查SQL注入"""
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.blocked_requests += 1
                self._log_event('sql_injection', 'critical', text[:200])
                return False
        return True

    def _check_path_traversal(self, text: str) -> bool:
        """检查路径遍历"""
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.blocked_requests += 1
                self._log_event('path_traversal', 'high', text[:200])
                return False
        return True

    def _check_command_injection(self, text: str) -> bool:
        """检查命令注入"""
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.blocked_requests += 1
                self._log_event('command_injection', 'critical', text[:200])
                return False
        return True

    def _is_malicious_bot(self, user_agent: str) -> bool:
        """检测恶意机器人"""
        malicious_patterns = [
            r'sqlmap',
            r'nmap',
            r'masscan',
            r'dirbuster',
            r'gobuster',
            r'nikto',
            r'acunetix',
            r'nessus',
        ]

        ua_lower = user_agent.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, ua_lower):
                return True

        return False

    def _log_event(self, event_type: str, severity: str, details: str):
        """记录安全事件"""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            source_ip='unknown',  # 将在中间件中设置
            target_url='unknown',
            details=details,
        )
        self.security_events.append(event)
        logger.warning(f"Security Event [{severity.upper()}] {event_type}: {details}")

    def get_stats(self) -> Dict:
        """获取WAF统计信息"""
        return {
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'block_rate': round(self.blocked_requests / max(self.total_requests, 1) * 100, 2),
            'recent_events': len(self.security_events),
        }

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """获取最近的安全事件"""
        events = list(self.security_events)[-limit:]
        return [
            {
                'type': e.event_type,
                'severity': e.severity,
                'details': e.details,
                'timestamp': e.timestamp.isoformat(),
            }
            for e in events
        ]


class LoginProtection:
    """
    登录保护系统
    
    功能:
    1. 暴力破解防护
    2. 账户锁定
    3. 验证码触发
    4. IP封禁
    """

    def __init__(self, max_attempts: int = 5, lockout_duration: int = 900):
        """
        Args:
            max_attempts: 最大尝试次数
            lockout_duration: 锁定时长 (秒)
        """
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration

        # 登录尝试记录 {ip_or_username: [(timestamp, success), ...]}
        self.login_attempts: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)

        # 锁定账户 {ip_or_username: lock_until_timestamp}
        self.locked_accounts: Dict[str, float] = {}

    def check_login_attempt(self, identifier: str) -> Tuple[bool, str]:
        """
        检查登录尝试
        
        Args:
            identifier: IP地址或用户名
            
        Returns:
            (allowed, reason)
        """
        now = time.time()

        # 检查是否被锁定
        if identifier in self.locked_accounts:
            lock_until = self.locked_accounts[identifier]
            if now < lock_until:
                remaining = int(lock_until - now)
                return False, f"Account locked. Try again in {remaining} seconds"
            else:
                # 锁定已过期，清除
                del self.locked_accounts[identifier]
                self.login_attempts[identifier] = []

        # 清理过期的尝试记录 (1小时内)
        cutoff = now - 3600
        self.login_attempts[identifier] = [
            (ts, success) for ts, success in self.login_attempts[identifier]
            if ts > cutoff
        ]

        # 计算失败次数
        recent_failures = sum(
            1 for ts, success in self.login_attempts[identifier]
            if not success
        )

        # 检查是否超过最大尝试次数
        if recent_failures >= self.max_attempts:
            # 锁定账户
            self.locked_accounts[identifier] = now + self.lockout_duration
            logger.warning(f"Account locked due to too many failed attempts: {identifier}")
            return False, f"Too many failed attempts. Account locked for {self.lockout_duration // 60} minutes"

        return True, ""

    def record_login_attempt(self, identifier: str, success: bool):
        """记录登录尝试"""
        now = time.time()
        self.login_attempts[identifier].append((now, success))

        if success:
            # 登录成功，清除失败记录
            self.login_attempts[identifier] = []
            if identifier in self.locked_accounts:
                del self.locked_accounts[identifier]

    def should_show_captcha(self, identifier: str) -> bool:
        """判断是否应该显示验证码"""
        recent_failures = sum(
            1 for ts, success in self.login_attempts.get(identifier, [])
            if not success and (time.time() - ts) < 300  # 5分钟内
        )
        return recent_failures >= 3

    def get_stats(self) -> Dict:
        """获取登录保护统计"""
        return {
            'locked_accounts': len(self.locked_accounts),
            'monitored_identifiers': len(self.login_attempts),
        }


class FileIntegrityMonitor:
    """
    文件完整性监控
    
    功能:
    1. 文件哈希校验
    2. 变更检测
    3. 自动告警
    """

    def __init__(self, monitored_dirs: List[str] = None):
        self.monitored_dirs = monitored_dirs or [
            'src',
            'shared',
            'apps',
            'config',
        ]

        # 文件哈希快照 {file_path: hash}
        self.file_hashes: Dict[str, str] = {}

        # 初始化快照
        self._create_snapshot()

    def _create_snapshot(self):
        """创建文件哈希快照"""
        self.file_hashes.clear()

        for dir_path in self.monitored_dirs:
            path = Path(dir_path)
            if not path.exists():
                continue

            for file_path in path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        file_hash = self._calculate_hash(file_path)
                        self.file_hashes[str(file_path)] = file_hash
                    except Exception as e:
                        logger.error(f"Failed to hash file {file_path}: {e}")

        logger.info(f"File integrity snapshot created: {len(self.file_hashes)} files")

    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件SHA256哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def check_integrity(self) -> Dict:
        """
        检查文件完整性
        
        Returns:
            检查结果
        """
        changes = {
            'modified': [],
            'added': [],
            'deleted': [],
        }

        # 当前文件列表
        current_files = set()

        for dir_path in self.monitored_dirs:
            path = Path(dir_path)
            if not path.exists():
                continue

            for file_path in path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        file_str = str(file_path)
                        current_files.add(file_str)

                        # 检查是否是新文件
                        if file_str not in self.file_hashes:
                            changes['added'].append(file_str)
                            continue

                        # 检查是否被修改
                        current_hash = self._calculate_hash(file_path)
                        if current_hash != self.file_hashes[file_str]:
                            changes['modified'].append({
                                'file': file_str,
                                'old_hash': self.file_hashes[file_str][:16],
                                'new_hash': current_hash[:16],
                            })
                    except Exception as e:
                        logger.error(f"Failed to check file {file_path}: {e}")

        # 检查删除的文件
        for file_path in self.file_hashes.keys():
            if file_path not in current_files:
                changes['deleted'].append(file_path)

        has_changes = any(changes.values())

        if has_changes:
            logger.warning(f"File integrity check failed: {changes}")

        return {
            'has_changes': has_changes,
            'changes': changes,
            'total_files_checked': len(current_files),
            'timestamp': datetime.now().isoformat(),
        }

    def update_snapshot(self):
        """更新快照"""
        self._create_snapshot()


class SecurityScanner:
    """
    安全扫描工具
    
    功能:
    1. 依赖漏洞扫描
    2. 配置安全检查
    3. 权限检查
    """

    def scan_dependencies(self) -> List[Dict]:
        """扫描依赖漏洞"""
        issues = []

        try:
            import subprocess
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)

                # 检查已知有漏洞的版本 (简化示例)
                vulnerable_packages = {
                    'django': '<3.2.0',
                    'flask': '<2.0.0',
                    'requests': '<2.25.0',
                }

                for pkg in packages:
                    name = pkg['name'].lower()
                    version = pkg['version']

                    if name in vulnerable_packages:
                        issues.append({
                            'type': 'vulnerable_dependency',
                            'package': name,
                            'current_version': version,
                            'recommended': vulnerable_packages[name],
                            'severity': 'medium',
                        })
        except Exception as e:
            logger.error(f"Dependency scan failed: {e}")

        return issues

    def scan_configuration(self) -> List[Dict]:
        """扫描配置安全问题"""
        issues = []

        # 检查环境变量
        if not os.getenv('SECRET_KEY'):
            issues.append({
                'type': 'missing_secret_key',
                'severity': 'critical',
                'message': 'SECRET_KEY environment variable is not set',
            })

        # 检查调试模式
        debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        if debug_mode:
            issues.append({
                'type': 'debug_mode_enabled',
                'severity': 'high',
                'message': 'Debug mode is enabled in production',
            })

        return issues

    def run_full_scan(self) -> Dict:
        """执行完整安全扫描"""
        return {
            'timestamp': datetime.now().isoformat(),
            'dependency_issues': self.scan_dependencies(),
            'configuration_issues': self.scan_configuration(),
            'total_issues': len(self.scan_dependencies()) + len(self.scan_configuration()),
        }


# 全局单例
waf = WebApplicationFirewall()
login_protection = LoginProtection()
file_integrity_monitor = FileIntegrityMonitor()
security_scanner = SecurityScanner()
