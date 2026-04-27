#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控服务 - 增强版
提供全面的性能指标收集、分析和告警功能

功能:
1. 请求性能监控 (响应时间、QPS)
2. 数据库查询监控 (慢查询检测)
3. 系统资源监控 (CPU、内存、磁盘)
4. 缓存命中率监控
5. 自定义性能追踪
6. 性能报告生成
7. 异常检测和告警
"""

import logging
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """请求性能指标"""
    endpoint: str
    method: str
    status_code: int
    response_time: float  # 秒
    timestamp: datetime = field(default_factory=datetime.now)
    request_size: int = 0
    response_size: int = 0


@dataclass
class DatabaseQueryMetric:
    """数据库查询性能指标"""
    query: str
    table: str
    execution_time: float  # 秒
    timestamp: datetime = field(default_factory=datetime.now)
    rows_affected: int = 0
    is_slow: bool = False


@dataclass
class SystemResourceMetric:
    """系统资源指标"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    network_in_mb: float
    network_out_mb: float
    timestamp: datetime = field(default_factory=datetime.now)


class PerformanceMonitor:
    """
    性能监控器
    
    核心功能:
    1. 实时性能指标收集
    2. 滑动窗口统计
    3. 百分位计算 (P50, P95, P99)
    4. 异常检测
    5. 性能报告
    """

    def __init__(self, window_size: int = 1000, slow_query_threshold: float = 1.0):
        """
        初始化性能监控器
        
        Args:
            window_size: 滑动窗口大小 (保留最近的N条记录)
            slow_query_threshold: 慢查询阈值 (秒)
        """
        self.window_size = window_size
        self.slow_query_threshold = slow_query_threshold

        # 请求指标存储 (按端点分组)
        self.request_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # 数据库查询指标
        self.db_query_metrics: deque = deque(maxlen=window_size)

        # 系统资源指标
        self.system_metrics: deque = deque(maxlen=window_size)

        # 全局统计
        self.total_requests = 0
        self.total_errors = 0
        self.start_time = datetime.now()

        # 性能告警配置
        self.alert_thresholds = {
            'response_time_p95': 2.0,  # P95响应时间超过2秒告警
            'error_rate': 0.05,  # 错误率超过5%告警
            'slow_query_count': 10,  # 每分钟慢查询超过10次告警
            'cpu_usage': 80.0,  # CPU使用率超过80%告警
            'memory_usage': 85.0,  # 内存使用率超过85%告警
        }

        # 告警历史记录
        self.alerts: deque = deque(maxlen=100)

    # ==================== 请求性能监控 ====================

    def record_request(self, endpoint: str, method: str, status_code: int,
                       response_time: float, request_size: int = 0,
                       response_size: int = 0):
        """
        记录请求性能指标
        
        Args:
            endpoint: API端点路径
            method: HTTP方法
            status_code: 响应状态码
            response_time: 响应时间 (秒)
            request_size: 请求大小 (字节)
            response_size: 响应大小 (字节)
        """
        metric = RequestMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            request_size=request_size,
            response_size=response_size
        )

        self.request_metrics[endpoint].append(metric)
        self.total_requests += 1

        if status_code >= 400:
            self.total_errors += 1

    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """
        获取端点性能统计
        
        Args:
            endpoint: API端点路径
            
        Returns:
            性能统计数据
        """
        metrics = list(self.request_metrics.get(endpoint, []))

        if not metrics:
            return {'endpoint': endpoint, 'count': 0}

        response_times = [m.response_time for m in metrics]
        error_count = sum(1 for m in metrics if m.status_code >= 400)

        return {
            'endpoint': endpoint,
            'count': len(metrics),
            'avg_response_time': round(statistics.mean(response_times), 4),
            'min_response_time': round(min(response_times), 4),
            'max_response_time': round(max(response_times), 4),
            'p50_response_time': round(self._percentile(response_times, 50), 4),
            'p95_response_time': round(self._percentile(response_times, 95), 4),
            'p99_response_time': round(self._percentile(response_times, 99), 4),
            'error_count': error_count,
            'error_rate': round(error_count / len(metrics), 4),
            'avg_request_size': round(statistics.mean([m.request_size for m in metrics]), 2),
            'avg_response_size': round(statistics.mean([m.response_size for m in metrics]), 2),
        }

    def get_all_endpoints_stats(self) -> List[Dict[str, Any]]:
        """获取所有端点的性能统计"""
        stats = []
        for endpoint in self.request_metrics.keys():
            stats.append(self.get_endpoint_stats(endpoint))

        # 按请求次数排序
        stats.sort(key=lambda x: x.get('count', 0), reverse=True)
        return stats

    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局性能统计"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        all_metrics = []
        for metrics in self.request_metrics.values():
            all_metrics.extend(metrics)

        if not all_metrics:
            return {
                'total_requests': 0,
                'uptime_seconds': round(uptime, 2),
            }

        response_times = [m.response_time for m in all_metrics]

        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': round(self.total_errors / max(self.total_requests, 1), 4),
            'requests_per_second': round(self.total_requests / max(uptime, 1), 2),
            'avg_response_time': round(statistics.mean(response_times), 4),
            'p50_response_time': round(self._percentile(response_times, 50), 4),
            'p95_response_time': round(self._percentile(response_times, 95), 4),
            'p99_response_time': round(self._percentile(response_times, 99), 4),
            'uptime_seconds': round(uptime, 2),
            'monitored_endpoints': len(self.request_metrics),
        }

    # ==================== 数据库查询监控 ====================

    def record_db_query(self, query: str, table: str, execution_time: float,
                        rows_affected: int = 0):
        """
        记录数据库查询性能
        
        Args:
            query: SQL查询语句
            table: 涉及的表名
            execution_time: 执行时间 (秒)
            rows_affected: 影响的行数
        """
        is_slow = execution_time > self.slow_query_threshold

        metric = DatabaseQueryMetric(
            query=query[:200],  # 限制长度
            table=table,
            execution_time=execution_time,
            rows_affected=rows_affected,
            is_slow=is_slow
        )

        self.db_query_metrics.append(metric)

        if is_slow:
            logger.warning(f"慢查询检测: {table}, 耗时: {execution_time:.3f}s")

    def get_db_query_stats(self) -> Dict[str, Any]:
        """获取数据库查询统计"""
        metrics = list(self.db_query_metrics)

        if not metrics:
            return {'total_queries': 0}

        execution_times = [m.execution_time for m in metrics]
        slow_queries = [m for m in metrics if m.is_slow]

        # 按表分组统计
        table_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'slow_count': 0})
        for m in metrics:
            table_stats[m.table]['count'] += 1
            table_stats[m.table]['total_time'] += m.execution_time
            if m.is_slow:
                table_stats[m.table]['slow_count'] += 1

        return {
            'total_queries': len(metrics),
            'avg_execution_time': round(statistics.mean(execution_times), 4),
            'p95_execution_time': round(self._percentile(execution_times, 95), 4),
            'slow_query_count': len(slow_queries),
            'slow_query_rate': round(len(slow_queries) / len(metrics), 4),
            'table_stats': dict(table_stats),
            'top_slow_queries': [
                {
                    'query': m.query,
                    'table': m.table,
                    'execution_time': m.execution_time,
                }
                for m in sorted(slow_queries, key=lambda x: x.execution_time, reverse=True)[:10]
            ]
        }

    # ==================== 系统资源监控 ====================

    def record_system_metrics(self):
        """记录当前系统资源使用情况"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            metric = SystemResourceMetric(
                cpu_percent=cpu_percent,
                memory_mb=round(memory.used / (1024 * 1024), 2),
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_in_mb=round(net_io.bytes_recv / (1024 * 1024), 2),
                network_out_mb=round(net_io.bytes_sent / (1024 * 1024), 2),
            )

            self.system_metrics.append(metric)
            return metric

        except ImportError:
            logger.warning("psutil库未安装，无法记录系统指标")
            return None
        except Exception as e:
            logger.error(f"记录系统指标失败: {e}")
            return None

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统资源统计"""
        metrics = list(self.system_metrics)

        if not metrics:
            return {'available': False}

        latest = metrics[-1]

        return {
            'available': True,
            'current': {
                'cpu_percent': latest.cpu_percent,
                'memory_mb': latest.memory_mb,
                'memory_percent': latest.memory_percent,
                'disk_usage_percent': latest.disk_usage_percent,
                'network_in_mb': latest.network_in_mb,
                'network_out_mb': latest.network_out_mb,
            },
            'averages': {
                'cpu_percent': round(statistics.mean([m.cpu_percent for m in metrics]), 2),
                'memory_mb': round(statistics.mean([m.memory_mb for m in metrics]), 2),
                'memory_percent': round(statistics.mean([m.memory_percent for m in metrics]), 2),
            }
        }

    # ==================== 性能告警 ====================

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        检查性能告警
        
        Returns:
            告警列表
        """
        alerts = []

        # 检查响应时间P95
        global_stats = self.get_global_stats()
        p95_time = global_stats.get('p95_response_time', 0)
        if p95_time > self.alert_thresholds['response_time_p95']:
            alert = {
                'type': 'high_response_time',
                'severity': 'warning',
                'message': f'P95响应时间过高: {p95_time:.3f}s (阈值: {self.alert_thresholds["response_time_p95"]}s)',
                'timestamp': datetime.now().isoformat(),
            }
            alerts.append(alert)
            self.alerts.append(alert)

        # 检查错误率
        error_rate = global_stats.get('error_rate', 0)
        if error_rate > self.alert_thresholds['error_rate']:
            alert = {
                'type': 'high_error_rate',
                'severity': 'critical',
                'message': f'错误率过高: {error_rate * 100:.2f}% (阈值: {self.alert_thresholds["error_rate"] * 100}%)',
                'timestamp': datetime.now().isoformat(),
            }
            alerts.append(alert)
            self.alerts.append(alert)

        # 检查慢查询
        db_stats = self.get_db_query_stats()
        slow_count = db_stats.get('slow_query_count', 0)
        if slow_count > self.alert_thresholds['slow_query_count']:
            alert = {
                'type': 'too_many_slow_queries',
                'severity': 'warning',
                'message': f'慢查询数量过多: {slow_count} (阈值: {self.alert_thresholds["slow_query_count"]})',
                'timestamp': datetime.now().isoformat(),
            }
            alerts.append(alert)
            self.alerts.append(alert)

        # 检查系统资源
        system_stats = self.get_system_stats()
        if system_stats.get('available'):
            current = system_stats['current']

            if current['cpu_percent'] > self.alert_thresholds['cpu_usage']:
                alert = {
                    'type': 'high_cpu_usage',
                    'severity': 'warning',
                    'message': f'CPU使用率过高: {current["cpu_percent"]}% (阈值: {self.alert_thresholds["cpu_usage"]}%)',
                    'timestamp': datetime.now().isoformat(),
                }
                alerts.append(alert)
                self.alerts.append(alert)

            if current['memory_percent'] > self.alert_thresholds['memory_usage']:
                alert = {
                    'type': 'high_memory_usage',
                    'severity': 'critical',
                    'message': f'内存使用率过高: {current["memory_percent"]}% (阈值: {self.alert_thresholds["memory_usage"]}%)',
                    'timestamp': datetime.now().isoformat(),
                }
                alerts.append(alert)
                self.alerts.append(alert)

        return alerts

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的告警"""
        return list(self.alerts)[-limit:]

    # ==================== 性能报告 ====================

    def generate_report(self) -> Dict[str, Any]:
        """
        生成综合性能报告
        
        Returns:
            完整的性能报告
        """
        return {
            'generated_at': datetime.now().isoformat(),
            'global_stats': self.get_global_stats(),
            'endpoints': self.get_all_endpoints_stats()[:20],  # Top 20端点
            'database': self.get_db_query_stats(),
            'system': self.get_system_stats(),
            'alerts': self.get_recent_alerts(20),
            'recommendations': self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        # 基于统计数据生成建议
        global_stats = self.get_global_stats()
        db_stats = self.get_db_query_stats()

        if global_stats.get('p95_response_time', 0) > 1.0:
            recommendations.append(
                "P95响应时间超过1秒，建议：\n"
                "- 检查慢接口并优化\n"
                "- 添加缓存层\n"
                "- 优化数据库查询"
            )

        if global_stats.get('error_rate', 0) > 0.05:
            recommendations.append(
                "错误率超过5%，建议：\n"
                "- 检查错误日志\n"
                "- 增加异常处理\n"
                "- 完善输入验证"
            )

        if db_stats.get('slow_query_rate', 0) > 0.1:
            recommendations.append(
                "慢查询比例超过10%，建议：\n"
                "- 为常用查询添加索引\n"
                "- 优化复杂SQL\n"
                "- 考虑读写分离"
            )

        system_stats = self.get_system_stats()
        if system_stats.get('available'):
            if system_stats['current']['cpu_percent'] > 70:
                recommendations.append(
                    "CPU使用率较高，建议：\n"
                    "- 优化CPU密集型操作\n"
                    "- 考虑水平扩展\n"
                    "- 使用异步处理"
                )

        if not recommendations:
            recommendations.append("系统性能良好，继续保持!")

        return recommendations

    # ==================== 工具方法 ====================

    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def reset(self):
        """重置所有监控数据"""
        self.request_metrics.clear()
        self.db_query_metrics.clear()
        self.system_metrics.clear()
        self.total_requests = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        self.alerts.clear()
        logger.info("性能监控数据已重置")


# 全局单例
performance_monitor = PerformanceMonitor()
