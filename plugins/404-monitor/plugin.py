"""
404监控器插件
监控和统计网站404错误，提供修复建议和热门404页面分析
"""

import threading
import time
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from shared.utils.plugin_database import plugin_db


class FortyFourMonitorPlugin(BasePlugin):
    """
    404监控器插件
    
    功能:
    1. 追踪404错误请求
    2. 统计404发生频率
    3. 识别热门404页面
    4. 提供修复建议（重定向规则）
    5. 生成404报告
    6. 实时告警功能
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="404监控器",
            slug="404-monitor",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_monitoring': True,
            'log_404_details': True,
            'alert_threshold': 50,  # 告警阈值（每小时404数量）
            'enable_alerts': True,
            'retention_days': 30,  # 数据保留天数
            'auto_suggest_redirects': True,  # 自动建议重定向
            'track_referrers': True,  # 跟踪来源页面
            'exclude_patterns': ['/favicon.ico', '/robots.txt'],  # 排除的路径模式
        }

        # 404记录列表
        self.forty_four_records: List[Dict[str, Any]] = []

        # 404统计 {url: count}
        self.forty_four_counts: Counter = Counter()

        # 来源统计 {referrer: count}
        self.referrer_stats: Counter = Counter()

        # 用户代理统计
        self.user_agent_stats: Counter = Counter()

        # 按小时的统计 {hour_timestamp: count}
        self.hourly_stats: Dict[str, int] = defaultdict(int)

        # 数据库持久化相关
        self.pending_records: List[Dict[str, Any]] = []  # 待持久化的记录队列
        self.db_flush_interval = 60  # 每60秒刷新一次到数据库
        self.last_db_flush = time.time()
        self.flush_lock = threading.Lock()  # 线程锁，避免并发问题

    def register_hooks(self):
        """注册钩子"""
        # 捕获404响应
        plugin_hooks.add_action(
            "response_404",
            self.on_404_error,
            priority=10
        )

        # 定期清理任务
        plugin_hooks.add_action(
            "daily_cleanup",
            self.cleanup_old_records,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()

        # 初始化数据库
        try:
            import importlib.util
            from pathlib import Path
            db_init_path = Path(__file__).parent / "db_init.py"
            spec = importlib.util.spec_from_file_location("db_init", db_init_path)
            db_init_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_init_module)
            db_init_module.init_404_monitor_db()
            print("[404Monitor] Database initialized")
        except Exception as e:
            print(f"[404Monitor] Warning: Database initialization failed: {e}")
        
        print("[404Monitor] Plugin activated - Monitoring enabled")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[404Monitor] Plugin deactivated")

    def on_404_error(self, error_data: Dict[str, Any]):
        """
        处理404错误
        
        Args:
            error_data: 错误数据 {url, ip, referrer, user_agent, timestamp, method}
        """
        if not self.settings.get('enable_monitoring'):
            return

        url = error_data.get('url', '')
        
        # 检查是否在排除列表中
        if self._should_exclude(url):
            return

        current_time = time.time()
        timestamp = error_data.get('timestamp', datetime.now().isoformat())

        # 记录404
        record = {
            'url': url,
            'ip': error_data.get('ip', ''),
            'referrer': error_data.get('referrer', ''),
            'user_agent': error_data.get('user_agent', ''),
            'method': error_data.get('method', 'GET'),
            'timestamp': timestamp,
            'timestamp_unix': current_time,
        }

        self.forty_four_records.append(record)

        # 更新统计
        self.forty_four_counts[url] += 1

        # 更新来源统计
        referrer = error_data.get('referrer', '')
        if referrer and self.settings.get('track_referrers'):
            self.referrer_stats[referrer] += 1

        # 更新用户代理统计
        user_agent = error_data.get('user_agent', '')
        if user_agent:
            browser = self._extract_browser(user_agent)
            self.user_agent_stats[browser] += 1

        # 更新小时统计
        hour_key = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:00')
        self.hourly_stats[hour_key] += 1

        # 检查是否需要告警
        if self.settings.get('enable_alerts'):
            self._check_alert_threshold()

        # 限制记录数量（保留最近10000条）
        if len(self.forty_four_records) > 10000:
            self.forty_four_records = self.forty_four_records[-10000:]

        # 添加到待持久化队列
        self._queue_for_db_flush(record)

        print(f"[404Monitor] 404 detected: {url}")

    def get_404_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取404摘要统计
        
        Args:
            hours: 统计时长（小时）
            
        Returns:
            统计数据
        """
        cutoff_time = time.time() - (hours * 3600)

        # 过滤指定时间范围内的记录
        recent_records = [
            record for record in self.forty_four_records
            if record['timestamp_unix'] > cutoff_time
        ]

        total_404s = len(recent_records)
        unique_urls = len(set(record['url'] for record in recent_records))
        unique_ips = len(set(record['ip'] for record in recent_records if record['ip']))

        # 计算增长率（与前一周期对比）
        previous_cutoff = cutoff_time - (hours * 3600)
        previous_records = [
            record for record in self.forty_four_records
            if previous_cutoff < record['timestamp_unix'] <= cutoff_time
        ]
        previous_count = len(previous_records)
        
        growth_rate = 0
        if previous_count > 0:
            growth_rate = ((total_404s - previous_count) / previous_count) * 100

        return {
            'total_404s': total_404s,
            'unique_urls': unique_urls,
            'unique_visitors': unique_ips,
            'period_hours': hours,
            'growth_rate': round(growth_rate, 2),
            'average_per_hour': round(total_404s / hours, 2) if hours > 0 else 0,
        }

    def get_top_404_pages(self, limit: int = 20, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最热门的404页面
        
        Args:
            limit: 返回数量
            hours: 统计时长
            
        Returns:
            热门404页面列表
        """
        cutoff_time = time.time() - (hours * 3600)

        # 统计URL出现次数
        url_counter = Counter()
        url_first_seen = {}
        url_last_seen = {}

        for record in self.forty_four_records:
            if record['timestamp_unix'] > cutoff_time:
                url = record['url']
                url_counter[url] += 1
                
                if url not in url_first_seen:
                    url_first_seen[url] = record['timestamp']
                url_last_seen[url] = record['timestamp']

        # 获取前N个
        top_pages = []
        for url, count in url_counter.most_common(limit):
            suggestions = []
            if self.settings.get('auto_suggest_redirects'):
                suggestions = self._generate_redirect_suggestions(url)

            top_pages.append({
                'url': url,
                'count': count,
                'first_seen': url_first_seen.get(url),
                'last_seen': url_last_seen.get(url),
                'suggestions': suggestions,
            })

        return top_pages

    def get_referrer_stats(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取来源页面统计
        
        Args:
            limit: 返回数量
            hours: 统计时长
            
        Returns:
            来源统计列表
        """
        if not self.settings.get('track_referrers'):
            return []

        cutoff_time = time.time() - (hours * 3600)

        # 重新统计
        referrer_counter = Counter()
        for record in self.forty_four_records:
            if record['timestamp_unix'] > cutoff_time:
                referrer = record.get('referrer', '')
                if referrer:
                    referrer_counter[referrer] += 1

        # 转换为列表
        result = []
        for referrer, count in referrer_counter.most_common(limit):
            result.append({
                'referrer': referrer,
                'count': count,
                'domain': self._extract_domain(referrer),
            })

        return result

    def get_hourly_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取小时趋势
        
        Args:
            hours: 统计时长
            
        Returns:
            趋势数据列表
        """
        trend = []
        current_time = time.time()

        for i in range(hours, 0, -1):
            hour_time = current_time - (i * 3600)
            hour_key = datetime.fromtimestamp(hour_time).strftime('%Y-%m-%d %H:00')
            
            count = self.hourly_stats.get(hour_key, 0)
            
            trend.append({
                'hour': hour_key,
                'count': count,
                'timestamp': hour_time,
            })

        return trend

    def get_redirect_suggestions(self, url: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取重定向建议
        
        Args:
            url: 特定URL，如果为None则返回所有建议
            limit: 返回数量
            
        Returns:
            重定向建议列表
        """
        if not self.settings.get('auto_suggest_redirects'):
            return []

        suggestions = []

        if url:
            # 为特定URL生成建议
            suggested_redirects = self._generate_redirect_suggestions(url)
            for suggestion in suggested_redirects:
                suggestions.append({
                    'from_url': url,
                    'to_url': suggestion,
                    'confidence': self._calculate_confidence(url, suggestion),
                    'type': self._get_suggestion_type(url, suggestion),
                })
        else:
            # 为热门404页面生成建议
            top_pages = self.get_top_404_pages(limit=limit)
            for page in top_pages:
                suggested_redirects = self._generate_redirect_suggestions(page['url'])
                for suggestion in suggested_redirects[:1]:  # 只取最佳建议
                    suggestions.append({
                        'from_url': page['url'],
                        'to_url': suggestion,
                        'count': page['count'],
                        'confidence': self._calculate_confidence(page['url'], suggestion),
                        'type': self._get_suggestion_type(page['url'], suggestion),
                    })

        return suggestions

    def export_404_report(self, format: str = 'json', hours: int = 24) -> Any:
        """
        导出404报告
        
        Args:
            format: 导出格式 (json, csv)
            hours: 统计时长
            
        Returns:
            导出的数据
        """
        cutoff_time = time.time() - (hours * 3600)

        recent_records = [
            record for record in self.forty_four_records
            if record['timestamp_unix'] > cutoff_time
        ]

        if format == 'json':
            import json
            return json.dumps(recent_records, indent=2, ensure_ascii=False)
        
        elif format == 'csv':
            import csv
            import io

            if not recent_records:
                return ""

            output = io.StringIO()
            fieldnames = ['timestamp', 'url', 'ip', 'referrer', 'method', 'user_agent']
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')

            writer.writeheader()
            for record in recent_records:
                writer.writerow(record)

            return output.getvalue()

        return None

    def cleanup_old_records(self):
        """清理过期记录"""
        retention_days = self.settings.get('retention_days', 30)
        cutoff_time = time.time() - (retention_days * 86400)

        # 清理404记录
        self.forty_four_records = [
            record for record in self.forty_four_records
            if record['timestamp_unix'] > cutoff_time
        ]

        # 清理小时统计
        old_hours = [
            key for key in self.hourly_stats.keys()
            if datetime.strptime(key, '%Y-%m-%d %H:%M').timestamp() < cutoff_time
        ]
        for key in old_hours:
            del self.hourly_stats[key]

        print(f"[404Monitor] Cleaned up records older than {retention_days} days")

    def _should_exclude(self, url: str) -> bool:
        """
        判断是否应该排除此URL
        
        Args:
            url: URL地址
            
        Returns:
            是否应该排除
        """
        exclude_patterns = self.settings.get('exclude_patterns', [])
        return any(pattern in url for pattern in exclude_patterns)

    def _check_alert_threshold(self):
        """检查是否达到告警阈值"""
        current_time = time.time()
        one_hour_ago = current_time - 3600

        # 统计最近1小时的404数量
        recent_count = sum(
            1 for record in self.forty_four_records
            if record['timestamp_unix'] > one_hour_ago
        )

        threshold = self.settings.get('alert_threshold', 50)
        
        if recent_count >= threshold:
            self._send_alert(recent_count, threshold)

    def _send_alert(self, count: int, threshold: int):
        """
        发送告警
        
        Args:
            count: 当前数量
            threshold: 阈值
        """
        alert_message = (
            f"⚠️ 404错误告警\n"
            f"过去1小时内404数量: {count}\n"
            f"阈值: {threshold}\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"建议: 检查热门404页面并设置重定向"
        )
        print(f"[404Monitor] ALERT: {alert_message}")
        # 通知功能待实现：需要集成邮件/短信通知系统

    def _generate_redirect_suggestions(self, url: str) -> List[str]:
        """
        生成重定向建议
        
        Args:
            url: 404的URL
            
        Returns:
            建议的重定向目标列表
        """
        suggestions = []

        # 1. 移除末尾的数字（可能是页码）
        import re
        cleaned = re.sub(r'/\d+/?$', '/', url)
        if cleaned != url:
            suggestions.append(cleaned)

        # 2. 移除查询参数
        if '?' in url:
            base_url = url.split('?')[0]
            suggestions.append(base_url)

        # 3. 尝试去掉最后一部分路径
        parts = url.rstrip('/').split('/')
        if len(parts) > 2:
            parent_url = '/'.join(parts[:-1]) + '/'
            suggestions.append(parent_url)

        # 4. 复数变单数（英文）
        if url.endswith('s/'):
            singular = url[:-2] + '/'
            suggestions.append(singular)

        # 5. 常见拼写错误修正
        common_typos = {
            '/artcles/': '/articles/',
            '/categroy/': '/category/',
            '/taggs/': '/tags/',
        }
        for typo, correct in common_typos.items():
            if typo in url:
                suggestions.append(url.replace(typo, correct))

        return suggestions[:5]  # 最多返回5个建议

    def _calculate_confidence(self, from_url: str, to_url: str) -> float:
        """
        计算建议的置信度
        
        Args:
            from_url: 原URL
            to_url: 目标URL
            
        Returns:
            置信度 (0-1)
        """
        # 简单的相似度计算
        if from_url == to_url:
            return 1.0

        # 基于路径相似度
        from_parts = set(from_url.split('/'))
        to_parts = set(to_url.split('/'))
        
        if not from_parts or not to_parts:
            return 0.0

        intersection = from_parts.intersection(to_parts)
        union = from_parts.union(to_parts)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0

        return round(jaccard_similarity, 2)

    def _get_suggestion_type(self, from_url: str, to_url: str) -> str:
        """
        获取建议类型
        
        Args:
            from_url: 原URL
            to_url: 目标URL
            
        Returns:
            建议类型
        """
        if from_url.split('?')[0] == to_url:
            return 'remove_query_params'
        elif to_url == '/'.join(from_url.split('/')[:-1]) + '/':
            return 'parent_page'
        else:
            return 'similar_url'

    def _extract_browser(self, user_agent: str) -> str:
        """
        从User Agent提取浏览器信息
        
        Args:
            user_agent: User Agent字符串
            
        Returns:
            浏览器名称
        """
        ua_lower = user_agent.lower()
        
        if 'chrome' in ua_lower and 'edge' not in ua_lower:
            return 'Chrome'
        elif 'firefox' in ua_lower:
            return 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            return 'Safari'
        elif 'edge' in ua_lower:
            return 'Edge'
        elif 'msie' in ua_lower or 'trident' in ua_lower:
            return 'Internet Explorer'
        else:
            return 'Other'

    def _extract_domain(self, url: str) -> str:
        """
        从URL提取域名
        
        Args:
            url: URL地址
            
        Returns:
            域名
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or url
        except:
            return url

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_monitoring',
                    'type': 'boolean',
                    'label': '启用404监控',
                },
                {
                    'key': 'log_404_details',
                    'type': 'boolean',
                    'label': '记录详细信息',
                    'help': '包括IP、User Agent等',
                },
                {
                    'key': 'alert_threshold',
                    'type': 'number',
                    'label': '告警阈值（每小时）',
                    'min': 10,
                    'max': 500,
                    'help': '超过此数量时发送告警',
                },
                {
                    'key': 'enable_alerts',
                    'type': 'boolean',
                    'label': '启用告警通知',
                },
                {
                    'key': 'retention_days',
                    'type': 'number',
                    'label': '数据保留天数',
                    'min': 7,
                    'max': 365,
                },
                {
                    'key': 'auto_suggest_redirects',
                    'type': 'boolean',
                    'label': '自动建议重定向',
                },
                {
                    'key': 'track_referrers',
                    'type': 'boolean',
                    'label': '跟踪来源页面',
                },
                {
                    'key': 'exclude_patterns',
                    'type': 'text',
                    'label': '排除的路径（逗号分隔）',
                    'help': '这些路径不会被记录',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看404统计',
                    'action': 'view_stats',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '查看热门404',
                    'action': 'view_top_404',
                    'variant': 'outline',
                },
                {
                    'type': 'button',
                    'label': '导出报告',
                    'action': 'export_report',
                    'variant': 'outline',
                },
            ]
        }

    def _queue_for_db_flush(self, record: Dict[str, Any]):
        """
        将记录添加到待持久化队列（无阻塞，快速返回）
        
        Args:
            record: 404 记录数据
        """
        with self.flush_lock:
            self.pending_records.append(record)

            # 检查是否需要立即刷新到数据库
            current_time = time.time()
            if (current_time - self.last_db_flush) >= self.db_flush_interval:
                # 异步执行，避免阻塞主线程
                thread = threading.Thread(target=self._flush_to_database, daemon=True)
                thread.start()

    def _flush_to_database(self):
        """
        将内存中的数据批量写入数据库（在后台线程中执行）
        这个过程是无感的，不会影响系统性能
        """
        try:
            with self.flush_lock:
                if not self.pending_records:
                    return

                # 取出所有待处理的记录
                records_to_save = self.pending_records.copy()
                self.pending_records.clear()

            # 批量插入数据库
            slug = "404-monitor"
            for record in records_to_save:
                try:
                    plugin_db.execute_update(slug, """
                                                   INSERT INTO forty_four_records
                                                       (url, ip, referrer, user_agent, method, timestamp, timestamp_unix)
                                                   VALUES (?, ?, ?, ?, ?, ?, ?)
                                                   """, (
                                                 record['url'],
                                                 record.get('ip', ''),
                                                 record.get('referrer', ''),
                                                 record.get('user_agent', ''),
                                                 record.get('method', 'GET'),
                                                 record['timestamp'],
                                                 record['timestamp_unix']
                                             ))
                except Exception as e:
                    print(f"[404Monitor] DB insert error: {e}")

            self.last_db_flush = time.time()
            print(f"[404Monitor] Flushed {len(records_to_save)} records to database")

        except Exception as e:
            print(f"[404Monitor] Flush to database failed: {e}")
            import traceback
            traceback.print_exc()

    def get_records_from_db(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        从数据库获取 404 记录
        
        Args:
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            404 记录列表
        """
        try:
            slug = "404-monitor"
            rows = plugin_db.execute_query(slug, """
                                                 SELECT id,
                                                        url,
                                                        ip,
                                                        referrer,
                                                        user_agent,
                                                        method,
                                                        timestamp,
                                                        timestamp_unix
                                                 FROM forty_four_records
                                                 ORDER BY timestamp_unix DESC
                                                 LIMIT ? OFFSET ?
                                                 """, (limit, offset))

            return [
                {
                    'id': row[0],
                    'url': row[1],
                    'ip': row[2],
                    'referrer': row[3],
                    'user_agent': row[4],
                    'method': row[5],
                    'timestamp': row[6],
                    'timestamp_unix': row[7],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[404Monitor] Failed to query database: {e}")
            return []

    def cleanup_old_records(self) -> int:
        """
        清理旧的 404 记录（同时清理内存和数据库）
        
        Returns:
            清理的记录数
        """
        retention_days = self.settings.get('retention_days', 30)
        cutoff_time = time.time() - (retention_days * 86400)

        cleaned_count = 0

        # 清理内存中的记录
        original_count = len(self.forty_four_records)
        self.forty_four_records = [
            record for record in self.forty_four_records
            if record['timestamp_unix'] > cutoff_time
        ]
        cleaned_count += original_count - len(self.forty_four_records)

        # 清理数据库中的记录
        try:
            slug = "404-monitor"
            result = plugin_db.execute_update(slug, """
                                                    DELETE
                                                    FROM forty_four_records
                                                    WHERE timestamp_unix < ?
                                                    """, (cutoff_time,))

            if result:
                db_cleaned = result.rowcount if hasattr(result, 'rowcount') else 0
                cleaned_count += db_cleaned
                print(f"[404Monitor] Cleaned {db_cleaned} old records from database")
        except Exception as e:
            print(f"[404Monitor] Failed to clean database: {e}")

        print(f"[404Monitor] Cleanup complete. Total cleaned: {cleaned_count} records")
        return cleaned_count


# 插件实例
plugin_instance = FortyFourMonitorPlugin()
