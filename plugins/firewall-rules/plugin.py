"""
防火墙规则插件
Web应用防火墙，提供IP黑名单、访问频率限制等安全功能
"""

import re
import time
import os
import gzip
import shutil
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Set
from pathlib import Path

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class FirewallRulesPlugin(BasePlugin):
    """
    防火墙规则插件
    
    功能:
    1. IP黑白名单管理
    2. 访问频率限制
    3. 恶意请求检测
    4. 地理位置封锁
    5. 攻击日志记录
    6. 自动封禁规则
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="防火墙规则",
            slug="firewall-rules",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_firewall': True,
            'enable_rate_limit': True,
            'rate_limit_requests': 100,  # 每分钟最大请求数
            'rate_limit_window': 60,  # 时间窗口(秒)
            'enable_ip_blacklist': True,
            'enable_ip_whitelist': True,
            'enable_geo_blocking': False,
            'blocked_countries': [],  # 封锁的国家代码
            'enable_auto_ban': True,
            'auto_ban_threshold': 50,  # 自动封禁阈值（异常请求数）
            'auto_ban_duration': 3600,  # 自动封禁时长(秒)
            'enable_sql_injection_protection': True,
            'enable_xss_protection': True,
            'enable_path_traversal_protection': True,
            'log_blocked_requests': True,
        }

        # IP黑名单
        self.ip_blacklist: Set[str] = set()

        # IP白名单
        self.ip_whitelist: Set[str] = set()

        # 访问记录 {ip: [timestamp, ...]}
        self.request_log: Dict[str, List[float]] = defaultdict(list)

        # 被封禁的IP {ip: unban_timestamp}
        self.banned_ips: Dict[str, float] = {}

        # 攻击日志
        self.attack_logs: List[Dict[str, Any]] = []

        # 可疑行为计数 {ip: count}
        self.suspicious_activity: Dict[str, int] = defaultdict(int)

        # IP地理位置数据库路径
        self.geoip_db_path = Path('plugins_data/firewall-rules/GeoLite2-City.mmdb')
        self.geoip_reader = None

        # 初始化地理位置数据库
        self._init_geoip_database()

    def register_hooks(self):
        """注册钩子"""
        # 请求前检查
        plugin_hooks.add_filter(
            "before_request",
            self.check_request,
            priority=1
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[FirewallRules] Plugin activated - Firewall enabled")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[FirewallRules] Plugin deactivated")

    def check_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查请求
        
        Args:
            request_data: 请求数据 {ip, url, method, headers, params, body}
            
        Returns:
            检查结果 {allowed: bool, reason: str, status_code: int}
        """
        if not self.settings.get('enable_firewall'):
            return {'allowed': True}

        ip = request_data.get('ip', '')
        url = request_data.get('url', '')
        method = request_data.get('method', 'GET')

        current_time = time.time()

        # 清理过期记录
        self._cleanup_old_records(current_time)

        # 1. 检查IP白名单（白名单直接放行）
        if self.settings.get('enable_ip_whitelist') and ip in self.ip_whitelist:
            return {'allowed': True, 'reason': 'IP whitelisted'}

        # 2. 检查IP是否被封禁
        if ip in self.banned_ips:
            unban_time = self.banned_ips[ip]
            if current_time < unban_time:
                remaining = int(unban_time - current_time)
                self._log_attack(ip, url, 'banned_ip', f'IP banned, {remaining}s remaining')
                return {
                    'allowed': False,
                    'reason': f'IP已被封禁，剩余 {remaining} 秒',
                    'status_code': 403,
                }
            else:
                # 封禁已过期
                del self.banned_ips[ip]

        # 3. 检查IP黑名单
        if self.settings.get('enable_ip_blacklist') and ip in self.ip_blacklist:
            self._log_attack(ip, url, 'blacklisted_ip', 'IP in blacklist')
            return {
                'allowed': False,
                'reason': 'IP在黑名单中',
                'status_code': 403,
            }

        # 4. 检查访问频率限制
        if self.settings.get('enable_rate_limit'):
            rate_check = self._check_rate_limit(ip, current_time)
            if not rate_check['allowed']:
                return rate_check

        # 5. 检查SQL注入
        if self.settings.get('enable_sql_injection_protection'):
            sqli_check = self._check_sql_injection(request_data)
            if not sqli_check['allowed']:
                return sqli_check

        # 6. 检查XSS攻击
        if self.settings.get('enable_xss_protection'):
            xss_check = self._check_xss(request_data)
            if not xss_check['allowed']:
                return xss_check

        # 7. 检查路径遍历
        if self.settings.get('enable_path_traversal_protection'):
            path_check = self._check_path_traversal(url)
            if not path_check['allowed']:
                return path_check

        # 8. 地理位置检查（简化实现）
        if self.settings.get('enable_geo_blocking'):
            geo_check = self._check_geo_location(ip)
            if not geo_check['allowed']:
                return geo_check

        return {'allowed': True}

    def add_to_blacklist(self, ip: str, reason: str = 'Manual addition') -> bool:
        """
        添加IP到黑名单
        
        Args:
            ip: IP地址
            reason: 原因
            
        Returns:
            是否成功添加
        """
        if ip in self.ip_whitelist:
            self.ip_whitelist.discard(ip)
        
        self.ip_blacklist.add(ip)
        self._log_attack(ip, '', 'blacklist_add', reason)
        print(f"[FirewallRules] Added to blacklist: {ip} - {reason}")
        return True

    def remove_from_blacklist(self, ip: str) -> bool:
        """
        从黑名单移除IP
        
        Args:
            ip: IP地址
            
        Returns:
            是否成功移除
        """
        if ip in self.ip_blacklist:
            self.ip_blacklist.discard(ip)
            print(f"[FirewallRules] Removed from blacklist: {ip}")
            return True
        return False

    def add_to_whitelist(self, ip: str, reason: str = 'Manual addition') -> bool:
        """
        添加IP到白名单
        
        Args:
            ip: IP地址
            reason: 原因
            
        Returns:
            是否成功添加
        """
        if ip in self.ip_blacklist:
            self.ip_blacklist.discard(ip)
        
        self.ip_whitelist.add(ip)
        print(f"[FirewallRules] Added to whitelist: {ip} - {reason}")
        return True

    def remove_from_whitelist(self, ip: str) -> bool:
        """
        从白名单移除IP
        
        Args:
            ip: IP地址
            
        Returns:
            是否成功移除
        """
        if ip in self.ip_whitelist:
            self.ip_whitelist.discard(ip)
            print(f"[FirewallRules] Removed from whitelist: {ip}")
            return True
        return False

    def ban_ip(self, ip: str, duration: int = 3600, reason: str = 'Auto ban') -> bool:
        """
        封禁IP
        
        Args:
            ip: IP地址
            duration: 封禁时长(秒)
            reason: 原因
            
        Returns:
            是否成功封禁
        """
        current_time = time.time()
        self.banned_ips[ip] = current_time + duration
        
        self._log_attack(ip, '', 'ip_ban', f'{reason}, duration: {duration}s')
        print(f"[FirewallRules] Banned IP: {ip} for {duration}s - {reason}")
        return True

    def unban_ip(self, ip: str) -> bool:
        """
        解封IP
        
        Args:
            ip: IP地址
            
        Returns:
            是否成功解封
        """
        if ip in self.banned_ips:
            del self.banned_ips[ip]
            print(f"[FirewallRules] Unbanned IP: {ip}")
            return True
        return False

    def get_security_stats(self) -> Dict[str, Any]:
        """
        获取安全统计
        
        Returns:
            统计数据
        """
        current_time = time.time()
        
        # 统计最近的攻击
        recent_attacks = [
            log for log in self.attack_logs
            if current_time - datetime.fromisoformat(log['timestamp']).timestamp() < 3600
        ]

        # 按类型分组
        attack_types = defaultdict(int)
        for attack in recent_attacks:
            attack_types[attack['type']] += 1

        # 被封禁的IP数量
        active_bans = sum(
            1 for unban_time in self.banned_ips.values()
            if unban_time > current_time
        )

        return {
            'enabled': self.settings.get('enable_firewall'),
            'total_blocked_1h': len(recent_attacks),
            'active_bans': active_bans,
            'blacklist_count': len(self.ip_blacklist),
            'whitelist_count': len(self.ip_whitelist),
            'attack_types': dict(attack_types),
            'top_attackers': self._get_top_attackers(),
            'settings': self.settings,
        }

    def get_attack_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取攻击日志
        
        Args:
            limit: 返回条数
            
        Returns:
            攻击日志列表
        """
        return self.attack_logs[-limit:]

    def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """
        获取被封禁的IP列表
        
        Returns:
            封禁列表
        """
        current_time = time.time()
        blocked = []

        for ip, unban_time in self.banned_ips.items():
            if unban_time > current_time:
                remaining = int(unban_time - current_time)
                blocked.append({
                    'ip': ip,
                    'unban_time': datetime.fromtimestamp(unban_time).isoformat(),
                    'remaining_seconds': remaining,
                    'remaining_formatted': self._format_duration(remaining),
                })

        return blocked

    def _check_rate_limit(self, ip: str, current_time: float) -> Dict[str, Any]:
        """
        检查访问频率限制
        
        Args:
            ip: IP地址
            current_time: 当前时间戳
            
        Returns:
            检查结果
        """
        window = self.settings.get('rate_limit_window', 60)
        max_requests = self.settings.get('rate_limit_requests', 100)

        # 清理过期的请求记录
        cutoff_time = current_time - window
        self.request_log[ip] = [
            timestamp for timestamp in self.request_log[ip]
            if timestamp > cutoff_time
        ]

        # 检查是否超过限制
        request_count = len(self.request_log[ip])
        if request_count >= max_requests:
            # 记录可疑行为
            self.suspicious_activity[ip] += 1
            
            # 检查是否需要自动封禁
            if self.settings.get('enable_auto_ban'):
                threshold = self.settings.get('auto_ban_threshold', 50)
                if self.suspicious_activity[ip] >= threshold:
                    ban_duration = self.settings.get('auto_ban_duration', 3600)
                    self.ban_ip(ip, ban_duration, f'Rate limit exceeded ({request_count} requests)')
            
            self._log_attack(ip, '', 'rate_limit', f'Too many requests: {request_count}/{max_requests}')
            
            return {
                'allowed': False,
                'reason': f'请求过于频繁，请稍后再试',
                'status_code': 429,
                'retry_after': window,
            }

        # 记录本次请求
        self.request_log[ip].append(current_time)

        return {'allowed': True}

    def _check_sql_injection(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查SQL注入
        
        Args:
            request_data: 请求数据
            
        Returns:
            检查结果
        """
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.*\b(FROM|INTO|TABLE|WHERE)\b)',
            r'(--|#|/\*|\*/)',
            r"(\bOR\b\s+\d+=\d+)",
            r"('\s*(OR|AND)\s+')",
            r'(;\s*(DROP|DELETE|UPDATE|INSERT))',
        ]

        # 检查URL参数
        url = request_data.get('url', '')
        params = str(request_data.get('params', ''))
        body = str(request_data.get('body', ''))

        check_string = f"{url} {params} {body}".lower()

        for pattern in sql_patterns:
            if re.search(pattern, check_string, re.IGNORECASE):
                ip = request_data.get('ip', '')
                self._log_attack(ip, url, 'sql_injection', f'SQL injection attempt detected')
                
                # 增加可疑计数
                self.suspicious_activity[ip] += 1
                
                return {
                    'allowed': False,
                    'reason': '检测到可疑请求',
                    'status_code': 403,
                }

        return {'allowed': True}

    def _check_xss(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查XSS攻击
        
        Args:
            request_data: 请求数据
            
        Returns:
            检查结果
        """
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on(load|error|click|mouseover)\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]

        url = request_data.get('url', '')
        params = str(request_data.get('params', ''))
        body = str(request_data.get('body', ''))

        check_string = f"{url} {params} {body}"

        for pattern in xss_patterns:
            if re.search(pattern, check_string, re.IGNORECASE):
                ip = request_data.get('ip', '')
                self._log_attack(ip, url, 'xss', f'XSS attempt detected')
                
                self.suspicious_activity[ip] += 1
                
                return {
                    'allowed': False,
                    'reason': '检测到可疑请求',
                    'status_code': 403,
                }

        return {'allowed': True}

    def _check_path_traversal(self, url: str) -> Dict[str, Any]:
        """
        检查路径遍历攻击
        
        Args:
            url: 请求URL
            
        Returns:
            检查结果
        """
        traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e/',
            r'\.\.%2f',
            r'/etc/passwd',
            r'/etc/shadow',
            r'\\windows\\',
        ]

        for pattern in traversal_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                self._log_attack('', url, 'path_traversal', f'Path traversal attempt detected')
                
                return {
                    'allowed': False,
                    'reason': '非法路径',
                    'status_code': 403,
                }

        return {'allowed': True}

    def _check_geo_location(self, ip: str) -> Dict[str, Any]:
        """
        检查地理位置
        
        Args:
            ip: IP地址
            
        Returns:
            检查结果
        """
        blocked_countries = self.settings.get('blocked_countries', [])

        if not blocked_countries:
            return {'allowed': True}

        # 获取IP的国家代码
        country_code = self._get_country_code(ip)

        if country_code and country_code.upper() in [c.upper() for c in blocked_countries]:
            self._log_attack(ip, '', 'geo_blocked', f'Blocked country: {country_code}')
            return {
                'allowed': False,
                'reason': f'访问被拒绝：来自受限地区',
                'status_code': 403,
            }

        return {'allowed': True}

    def _log_attack(self, ip: str, url: str, attack_type: str, details: str):
        """
        记录攻击日志
        
        Args:
            ip: IP地址
            url: URL
            attack_type: 攻击类型
            details: 详细信息
        """
        if not self.settings.get('log_blocked_requests'):
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ip': ip,
            'url': url,
            'type': attack_type,
            'details': details,
        }

        self.attack_logs.append(log_entry)

        # 限制日志数量（保留最近1000条）
        if len(self.attack_logs) > 1000:
            self.attack_logs = self.attack_logs[-1000:]

    def _get_top_attackers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取顶级攻击者
        
        Args:
            limit: 返回数量
            
        Returns:
            攻击者列表
        """
        attack_counts = defaultdict(int)
        
        for log in self.attack_logs:
            ip = log.get('ip', '')
            if ip:
                attack_counts[ip] += 1

        # 排序并返回前N个
        top_attackers = sorted(
            attack_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {'ip': ip, 'count': count}
            for ip, count in top_attackers
        ]

    def _cleanup_old_records(self, current_time: float):
        """清理过期记录"""
        # 清理过期的请求记录（保留1小时）
        cutoff_time = current_time - 3600
        
        ips_to_delete = []
        for ip, timestamps in self.request_log.items():
            self.request_log[ip] = [
                ts for ts in timestamps
                if ts > cutoff_time
            ]
            if not self.request_log[ip]:
                ips_to_delete.append(ip)

        for ip in ips_to_delete:
            del self.request_log[ip]

        # 清理过期的封禁
        expired_bans = [
            ip for ip, unban_time in self.banned_ips.items()
            if unban_time <= current_time
        ]
        for ip in expired_bans:
            del self.banned_ips[ip]

        # 清理可疑行为计数（1小时后重置）
        suspicious_cutoff = current_time - 3600
        # 简化实现：不清理，依靠自然增长

    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分钟"

    def _init_geoip_database(self):
        """初始化IP地理位置数据库"""
        try:
            # 确保目录存在
            self.geoip_db_path.parent.mkdir(parents=True, exist_ok=True)

            # 尝试导入maxminddb
            try:
                import maxminddb

                if self.geoip_db_path.exists():
                    self.geoip_reader = maxminddb.open_database(str(self.geoip_db_path))
                    print(f"[FirewallRules] GeoIP database loaded: {self.geoip_db_path}")
                else:
                    print(f"[FirewallRules] GeoIP database not found, please run update_geoip_database()")
            except ImportError:
                print("[FirewallRules] maxminddb not installed. Run: pip install maxminddb")
                print("[FirewallRules] GeoIP functionality will be disabled")
        except Exception as e:
            print(f"[FirewallRules] Failed to initialize GeoIP database: {e}")

    def _get_country_code(self, ip: str) -> str:
        """
        获取IP地址的国家代码
        
        Args:
            ip: IP地址
            
        Returns:
            国家代码（如 'CN', 'US'），失败返回 None
        """
        if not self.geoip_reader:
            return None

        try:
            result = self.geoip_reader.get(ip)
            if result and 'country' in result:
                return result['country'].get('iso_code')
        except Exception as e:
            print(f"[FirewallRules] GeoIP lookup failed for {ip}: {e}")

        return None

    def update_geoip_database(self, license_key: str = None) -> Dict[str, Any]:
        """
        更新IP地理位置数据库
        
        Args:
            license_key: MaxMind License Key（可选，默认为免费GeoLite2）
            
        Returns:
            更新结果
        """
        try:
            import urllib.request
            import tempfile

            # 确保目录存在
            self.geoip_db_path.parent.mkdir(parents=True, exist_ok=True)

            # MaxMind GeoLite2-City 下载URL
            # 注意：需要注册MaxMind账号获取License Key
            if not license_key:
                print("[FirewallRules] No license key provided. Please register at https://www.maxmind.com/")
                print("[FirewallRules] To get a free GeoLite2 license key")
                return {
                    'success': False,
                    'message': '需要提供MaxMind License Key。请访问 https://www.maxmind.com/ 注册获取'
                }

            download_url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"

            print(f"[FirewallRules] Downloading GeoIP database from MaxMind...")

            # 下载到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
                # 下载文件
                urllib.request.urlretrieve(download_url, tmp_file.name)

                # 解压tar.gz
                import tarfile
                with tarfile.open(tmp_file.name, 'r:gz') as tar:
                    # 查找.mmdb文件
                    mmdb_files = [f for f in tar.getnames() if f.endswith('.mmdb')]

                    if not mmdb_files:
                        return {'success': False, 'message': '未找到数据库文件'}

                    # 提取第一个.mmdb文件
                    mmdb_file = mmdb_files[0]
                    tar.extract(mmdb_file, path=str(self.geoip_db_path.parent))

                    # 移动到正确位置
                    extracted_path = self.geoip_db_path.parent / mmdb_file
                    if extracted_path.exists():
                        shutil.move(str(extracted_path), str(self.geoip_db_path))

            # 清理临时文件
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)

            # 重新加载数据库
            self._init_geoip_database()

            print(f"[FirewallRules] GeoIP database updated successfully")
            return {
                'success': True,
                'message': 'IP地理位置数据库更新成功',
                'path': str(self.geoip_db_path)
            }

        except Exception as e:
            print(f"[FirewallRules] Failed to update GeoIP database: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'更新失败: {str(e)}'
            }

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_firewall',
                    'type': 'boolean',
                    'label': '启用防火墙',
                },
                {
                    'key': 'enable_rate_limit',
                    'type': 'boolean',
                    'label': '启用访问频率限制',
                },
                {
                    'key': 'rate_limit_requests',
                    'type': 'number',
                    'label': '每分钟最大请求数',
                    'min': 10,
                    'max': 1000,
                    'show_if': {'enable_rate_limit': True},
                },
                {
                    'key': 'enable_ip_blacklist',
                    'type': 'boolean',
                    'label': '启用IP黑名单',
                },
                {
                    'key': 'enable_ip_whitelist',
                    'type': 'boolean',
                    'label': '启用IP白名单',
                },
                {
                    'key': 'enable_auto_ban',
                    'type': 'boolean',
                    'label': '启用自动封禁',
                    'help': '检测到异常行为时自动封禁IP',
                },
                {
                    'key': 'auto_ban_threshold',
                    'type': 'number',
                    'label': '自动封禁阈值',
                    'min': 10,
                    'max': 200,
                    'show_if': {'enable_auto_ban': True},
                },
                {
                    'key': 'enable_sql_injection_protection',
                    'type': 'boolean',
                    'label': 'SQL注入防护',
                },
                {
                    'key': 'enable_xss_protection',
                    'type': 'boolean',
                    'label': 'XSS攻击防护',
                },
                {
                    'key': 'enable_path_traversal_protection',
                    'type': 'boolean',
                    'label': '路径遍历防护',
                },
                {
                    'key': 'log_blocked_requests',
                    'type': 'boolean',
                    'label': '记录拦截日志',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看安全统计',
                    'action': 'view_stats',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '查看攻击日志',
                    'action': 'view_logs',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '管理黑名单',
                    'action': 'manage_blacklist',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '更新IP地理位置数据库',
                    'action': 'update_geoip',
                    'variant': 'primary',
                    'help': '需要MaxMind License Key',
                },
            ]
        }


# 插件实例
plugin_instance = FirewallRulesPlugin()
