"""
性能监控插件 (Performance Monitor)
提供页面加载时间监控、数据库查询监控、性能告警和优化建议功能
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class PerformanceMonitorPlugin(BasePlugin):
    """
    性能监控插件
    
    功能:
    1. 页面加载时间监控 - 追踪每个页面的加载速度
    2. 数据库查询监控 - 检测慢查询和频繁查询
    3. 性能告警 - 当性能下降时发送通知
    4. 优化建议 - 基于数据分析提供改进建议
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="性能监控",
            slug="performance-monitor",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_page_monitoring': True,
            'enable_db_monitoring': True,
            'slow_query_threshold': 100,  # 毫秒
            'page_load_threshold': 2,  # 秒
            'enable_alerts': True,
            'alert_email': '',
            'data_retention_days': 30,
            'sampling_rate': 100,  # 百分比
        }

        # 页面性能数据
        self.page_metrics: List[Dict[str, Any]] = []

        # 数据库查询记录
        self.db_queries: List[Dict[str, Any]] = []

        # 性能告警
        self.performance_alerts: List[Dict[str, Any]] = []

        # 系统资源监控
        self.system_metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_io': [],
        }

    def register_hooks(self):
        """注册钩子"""
        # 请求开始
        plugin_hooks.add_action(
            "request_started",
            self.on_request_start,
            priority=5
        )

        # 请求结束
        plugin_hooks.add_action(
            "request_finished",
            self.on_request_end,
            priority=10
        )

        # 数据库查询执行
        plugin_hooks.add_action(
            "db_query_executed",
            self.on_db_query,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[PerformanceMonitor] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[PerformanceMonitor] Plugin deactivated")

    def on_request_start(self, request_data: Dict[str, Any]):
        """请求开始时记录"""
        if not self.settings.get('enable_page_monitoring'):
            return

        request_data['_perf_start_time'] = time.time()
        request_data['_perf_start_memory'] = self._get_memory_usage()

    def on_request_end(self, request_data: Dict[str, Any], response_data: Dict[str, Any]):
        """请求结束时记录性能数据"""
        if not self.settings.get('enable_page_monitoring'):
            return

        start_time = request_data.get('_perf_start_time')
        if not start_time:
            return

        # 计算加载时间
        load_time = time.time() - start_time

        # 采样率控制
        import random
        if random.randint(1, 100) > self.settings.get('sampling_rate', 100):
            return

        # 记录页面性能
        metric = {
            'timestamp': datetime.now().isoformat(),
            'url': request_data.get('path', ''),
            'method': request_data.get('method', 'GET'),
            'load_time': round(load_time, 3),
            'status_code': response_data.get('status_code', 200),
            'response_size': response_data.get('content_length', 0),
            'user_agent': request_data.get('user_agent', ''),
            'ip': request_data.get('ip', ''),
        }

        self.page_metrics.append(metric)

        # 检查是否超过阈值
        threshold = self.settings.get('page_load_threshold', 2)
        if load_time > threshold:
            self._create_alert(
                alert_type='slow_page',
                severity='warning',
                message=f'Slow page load: {metric["url"]} took {load_time:.2f}s',
                details=metric
            )

        # 清理旧数据
        self._cleanup_old_data()

    def on_db_query(self, query_data: Dict[str, Any]):
        """记录数据库查询"""
        if not self.settings.get('enable_db_monitoring'):
            return

        execution_time = query_data.get('execution_time', 0) * 1000  # 转换为毫秒

        # 记录查询
        query_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query_data.get('sql', ''),
            'execution_time_ms': round(execution_time, 2),
            'rows_affected': query_data.get('rows', 0),
            'table': self._extract_table_name(query_data.get('sql', '')),
        }

        self.db_queries.append(query_record)

        # 检查是否是慢查询
        slow_threshold = self.settings.get('slow_query_threshold', 100)
        if execution_time > slow_threshold:
            self._create_alert(
                alert_type='slow_query',
                severity='warning',
                message=f'Slow query detected: {execution_time:.0f}ms',
                details=query_record
            )

        # 清理旧数据
        self._cleanup_old_data()

    def get_page_performance_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取页面性能统计
        
        Args:
            hours: 统计时间范围(小时)
            
        Returns:
            统计数据
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_metrics = [
            m for m in self.page_metrics
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]

        if not recent_metrics:
            return {
                'total_requests': 0,
                'avg_load_time': 0,
                'p95_load_time': 0,
                'p99_load_time': 0,
                'slowest_pages': [],
            }

        # 计算统计数据
        load_times = [m['load_time'] for m in recent_metrics]
        load_times_sorted = sorted(load_times)

        total_requests = len(recent_metrics)
        avg_load_time = sum(load_times) / total_requests
        p95_index = int(total_requests * 0.95)
        p99_index = int(total_requests * 0.99)
        p95_load_time = load_times_sorted[min(p95_index, total_requests - 1)]
        p99_load_time = load_times_sorted[min(p99_index, total_requests - 1)]

        # 最慢的页面
        slowest_pages = sorted(
            recent_metrics,
            key=lambda x: x['load_time'],
            reverse=True
        )[:10]

        # 按URL分组统计
        by_url = defaultdict(list)
        for m in recent_metrics:
            by_url[m['url']].append(m['load_time'])

        avg_by_url = {
            url: round(sum(times) / len(times), 3)
            for url, times in by_url.items()
        }

        return {
            'total_requests': total_requests,
            'avg_load_time': round(avg_load_time, 3),
            'p95_load_time': round(p95_load_time, 3),
            'p99_load_time': round(p99_load_time, 3),
            'min_load_time': round(min(load_times), 3),
            'max_load_time': round(max(load_times), 3),
            'slowest_pages': slowest_pages,
            'avg_by_url': dict(sorted(avg_by_url.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def get_db_performance_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取数据库性能统计
        
        Args:
            hours: 统计时间范围(小时)
            
        Returns:
            统计数据
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_queries = [
            q for q in self.db_queries
            if datetime.fromisoformat(q['timestamp']) > cutoff_time
        ]

        if not recent_queries:
            return {
                'total_queries': 0,
                'avg_execution_time': 0,
                'slow_queries': 0,
                'slowest_queries': [],
            }

        # 计算统计数据
        execution_times = [q['execution_time_ms'] for q in recent_queries]

        total_queries = len(recent_queries)
        avg_execution_time = sum(execution_times) / total_queries
        slow_threshold = self.settings.get('slow_query_threshold', 100)
        slow_queries = len([t for t in execution_times if t > slow_threshold])

        # 最慢的查询
        slowest_queries = sorted(
            recent_queries,
            key=lambda x: x['execution_time_ms'],
            reverse=True
        )[:10]

        # 按表分组统计
        by_table = defaultdict(lambda: {'count': 0, 'total_time': 0})
        for q in recent_queries:
            table = q.get('table', 'unknown')
            by_table[table]['count'] += 1
            by_table[table]['total_time'] += q['execution_time_ms']

        table_stats = {
            table: {
                'count': data['count'],
                'avg_time': round(data['total_time'] / data['count'], 2)
            }
            for table, data in by_table.items()
        }

        return {
            'total_queries': total_queries,
            'avg_execution_time': round(avg_execution_time, 2),
            'max_execution_time': round(max(execution_times), 2),
            'slow_queries': slow_queries,
            'slow_query_percentage': round((slow_queries / total_queries * 100), 2),
            'slowest_queries': slowest_queries,
            'by_table': dict(sorted(table_stats.items(), key=lambda x: x[1]['avg_time'], reverse=True)),
        }

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        suggestions = []

        # 分析页面性能
        page_stats = self.get_page_performance_stats(hours=24)
        if page_stats['total_requests'] > 0:
            avg_load = page_stats['avg_load_time']
            if avg_load > 2:
                suggestions.append({
                    'type': 'page_performance',
                    'severity': 'high',
                    'title': '页面加载速度较慢',
                    'description': f'平均加载时间为{avg_load:.2f}秒，建议优化到2秒以内',
                    'recommendations': [
                        '启用图片懒加载',
                        '压缩CSS和JavaScript文件',
                        '使用CDN加速静态资源',
                        '启用浏览器缓存',
                    ]
                })

        # 分析数据库性能
        db_stats = self.get_db_performance_stats(hours=24)
        if db_stats['total_queries'] > 0:
            slow_pct = db_stats['slow_query_percentage']
            if slow_pct > 5:
                suggestions.append({
                    'type': 'database_performance',
                    'severity': 'high',
                    'title': '慢查询比例过高',
                    'description': f'{slow_pct:.1f}%的查询超过阈值，需要优化',
                    'recommendations': [
                        '为常用查询字段添加索引',
                        '优化复杂查询语句',
                        '使用查询缓存',
                        '考虑读写分离',
                    ]
                })

            # 检查高频访问的表
            for table, stats in db_stats.get('by_table', {}).items():
                if stats['count'] > 1000 and stats['avg_time'] > 50:
                    suggestions.append({
                        'type': 'table_optimization',
                        'severity': 'medium',
                        'title': f'表 "{table}" 需要优化',
                        'description': f'该表有{stats["count"]}次查询，平均耗时{stats["avg_time"]:.0f}ms',
                        'recommendations': [
                            f'为表 "{table}" 添加合适的索引',
                            '考虑分区或分表',
                            '优化相关查询逻辑',
                        ]
                    })

        # 内存使用建议
        memory_usage = self._get_memory_usage()
        if memory_usage > 80:
            suggestions.append({
                'type': 'memory_usage',
                'severity': 'medium',
                'title': '内存使用率较高',
                'description': f'当前内存使用率为{memory_usage:.1f}%',
                'recommendations': [
                    '检查是否有内存泄漏',
                    '优化大数据集处理',
                    '增加服务器内存',
                ]
            })

        return suggestions

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取性能告警"""
        sorted_alerts = sorted(
            self.performance_alerts,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        return sorted_alerts[:limit]

    def _create_alert(self, alert_type: str, severity: str, message: str, details: Dict[str, Any] = None):
        """创建性能告警"""
        if not self.settings.get('enable_alerts'):
            return

        alert = {
            'id': len(self.performance_alerts) + 1,
            'type': alert_type,
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {},
            'acknowledged': False,
        }

        self.performance_alerts.append(alert)

        # 发送邮件通知
        if self.settings.get('alert_email'):
            self._send_alert_email(alert)

        print(f"[PerformanceMonitor] Alert: {message}")

    def _send_alert_email(self, alert: Dict[str, Any]):
        """发送告警邮件(模拟)"""
        email = self.settings.get('alert_email', '')
        print(f"[PerformanceMonitor] Would send alert email to {email}: {alert['message']}")

    def _cleanup_old_data(self):
        """清理过期数据"""
        retention_days = self.settings.get('data_retention_days', 30)
        cutoff_time = datetime.now() - timedelta(days=retention_days)

        # 清理页面指标
        self.page_metrics = [
            m for m in self.page_metrics
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]

        # 清理数据库查询记录
        self.db_queries = [
            q for q in self.db_queries
            if datetime.fromisoformat(q['timestamp']) > cutoff_time
        ]

        # 清理告警(保留90天)
        alert_cutoff = datetime.now() - timedelta(days=90)
        self.performance_alerts = [
            a for a in self.performance_alerts
            if datetime.fromisoformat(a['timestamp']) > alert_cutoff
        ]

    def _get_memory_usage(self) -> float:
        """获取内存使用率(模拟)"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent
        except ImportError:
            return 0.0

    def _extract_table_name(self, sql: str) -> str:
        """从SQL中提取表名"""
        sql_lower = sql.lower().strip()

        # SELECT ... FROM table
        if sql_lower.startswith('select'):
            parts = sql_lower.split('from')
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.strip('`"[]')

        # INSERT INTO table
        elif sql_lower.startswith('insert'):
            parts = sql_lower.split('into')
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.strip('`"[]')

        # UPDATE table
        elif sql_lower.startswith('update'):
            table_part = sql_lower.split()[1]
            return table_part.strip('`"[]')

        # DELETE FROM table
        elif sql_lower.startswith('delete'):
            parts = sql_lower.split('from')
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.strip('`"[]')

        return 'unknown'

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_page_monitoring',
                    'type': 'boolean',
                    'label': '启用页面加载监控',
                },
                {
                    'key': 'enable_db_monitoring',
                    'type': 'boolean',
                    'label': '启用数据库查询监控',
                },
                {
                    'key': 'slow_query_threshold',
                    'type': 'number',
                    'label': '慢查询阈值(毫秒)',
                    'min': 10,
                    'max': 5000,
                },
                {
                    'key': 'page_load_threshold',
                    'type': 'number',
                    'label': '页面加载阈值(秒)',
                    'min': 0.5,
                    'max': 10,
                },
                {
                    'key': 'enable_alerts',
                    'type': 'boolean',
                    'label': '启用性能告警',
                },
                {
                    'key': 'alert_email',
                    'type': 'text',
                    'label': '告警邮箱',
                },
                {
                    'key': 'data_retention_days',
                    'type': 'number',
                    'label': '数据保留天数',
                    'min': 7,
                    'max': 90,
                },
                {
                    'key': 'sampling_rate',
                    'type': 'number',
                    'label': '采样率(%)',
                    'min': 1,
                    'max': 100,
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看性能报告',
                    'action': 'view_report',
                    'variant': 'default',
                },
                {
                    'type': 'button',
                    'label': '获取优化建议',
                    'action': 'get_suggestions',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = PerformanceMonitorPlugin()
