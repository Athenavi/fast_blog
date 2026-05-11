import gzip
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class AsyncLogQueue:
    """异步日志队列（简化版）"""

    def __init__(self, max_size: int = 1000):
        self.queue = []
        self.max_size = max_size

    def put(self, record):
        if len(self.queue) >= self.max_size:
            self.queue.pop(0)  # 移除最旧的日志
        self.queue.append(record)

    def get_all(self):
        records = self.queue.copy()
        self.queue.clear()
        return records


class CompressedRotatingFileHandler(RotatingFileHandler):
    """支持压缩的轮转文件处理器"""

    def doRollover(self):
        """执行日志轮转并压缩旧文件"""
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore

        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

            # 压缩当前日志文件
            dfn = self.rotation_filename(self.baseFilename + ".1.gz")
            if os.path.exists(dfn):
                os.remove(dfn)

            # 压缩原文件
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(dfn, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)  # type: ignore

            # 删除原文件
            os.remove(self.baseFilename)

        if not self.delay:
            self.stream = self._open()


class OptimizedStructuredFormatter(logging.Formatter):
    """优化的结构化日志格式化器"""

    MAX_MSG_SIZE = 1024  # 减少到1KB

    def format(self, record):
        # 截断超大消息
        msg = record.getMessage()
        if len(msg) > self.MAX_MSG_SIZE:
            record.msg = msg[:self.MAX_MSG_SIZE] + "...[TRUNCATED]"

        # 简化的日志结构
        log_data = {
            'ts': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname[0],  # 只保留首字母
            'msg': record.getMessage(),
            'loc': f"{record.module}:{record.lineno}"
        }

        # 只在错误时添加详细信息
        if record.levelno >= logging.ERROR:
            log_data.update({
                'func': record.funcName,
                'thread': record.threadName
            })

        # 添加自定义字段（如果有）
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))


def cleanup_old_logs(log_dir, pattern="app_*.log*", max_age_days=7):
    """清理旧的日志文件"""
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    current_time = datetime.now()
    cleaned_files = []
    total_size_freed = 0

    for log_file in log_path.glob(pattern):
        try:
            file_age = current_time - datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_age.days > max_age_days:
                file_size = log_file.stat().st_size
                log_file.unlink()
                cleaned_files.append(str(log_file))
                total_size_freed += file_size
        except Exception as e:
            logging.warning(f"清理文件 {log_file} 时出错: {e}")

    if cleaned_files:
        logging.info(f"清理了 {len(cleaned_files)} 个旧日志文件，释放空间: {total_size_freed / (1024 * 1024):.2f} MB")
        for file in cleaned_files:
            logging.info(f"  - {file}")


def init_optimized_logger(
        log_dir="logs",
        log_name="app.log",  # 固定文件名
        max_bytes=5 * 1024 * 1024,  # 减少到5MB
        backup_count=3,  # 减少备份数量
        log_level=logging.INFO,
        enable_compression=True,
        cleanup_old=True
):
    """初始化优化的日志系统"""

    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)

    # 清理旧日志文件
    if cleanup_old:
        cleanup_old_logs(log_dir)

    # 检查磁盘空间
    try:
        total, used, free = shutil.disk_usage(log_dir)
        free_mb = free / (1024 * 1024)
        if free_mb < 50:  # 至少需要50MB空间
            raise RuntimeError(f"磁盘空间不足: 仅剩 {free_mb:.2f}MB")
    except Exception as e:
        logging.warning(f"磁盘空间检查失败: {e}")

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # 清除现有处理器
    root_logger.setLevel(log_level)

    # 创建优化的格式化器
    formatter = OptimizedStructuredFormatter()

    # 文件处理器 - 使用固定文件名
    log_path = os.path.join(log_dir, log_name)

    if enable_compression:
        file_handler = CompressedRotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 简化的控制台处理器 - 强制使用 UTF-8 编码
    console_handler = logging.StreamHandler(sys.stdout)
    # Windows 下设置 UTF-8 编码，确保兼容所有字符
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass  # 如果 reconfigure 失败，继续使用默认编码
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 设置文件权限
    try:
        os.chmod(log_path, 0o644)
    except (OSError, PermissionError) as e:
        root_logger.warning(f"无法设置文件权限: {e}")
        pass

    root_logger.info(f"优化日志系统已启动 - 文件: {log_path}, 大小限制: {max_bytes / (1024 * 1024):.1f}MB")

    return root_logger


def init_pythonanywhere_logger():
    """初始化优化日志配置，避免递归问题"""

    # 获取根日志记录器
    no_record_logger = logging.getLogger()

    # 清除现有的处理器，避免重复
    for handler in no_record_logger.handlers[:]:
        no_record_logger.removeHandler(handler)

    # 设置日志级别
    no_record_logger.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建控制台处理器（避免文件写入权限问题）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    no_record_logger.addHandler(console_handler)

    # 禁用过于冗长的日志记录器
    logging.getLogger('waitress').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    logging.info("Logger initialized successfully without recursion issues")

    # 关键修复：返回 logger 对象
    return no_record_logger


# 新增Prometheus指标监控
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    import time

    # 定义监控指标
    REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('app_request_duration_seconds', 'Request duration')
    ACTIVE_CONNECTIONS = Gauge('app_active_connections', 'Active connections')
    LOG_ENTRIES = Counter('app_log_entries_total', 'Total log entries', ['level'])
    REQUEST_SIZE = Summary('app_request_size_bytes', 'Request size')
    RESPONSE_SIZE = Summary('app_request_size_bytes', 'Response size')


    # 重写日志处理类以添加监控
    class MonitoredRotatingFileHandler(RotatingFileHandler):
        def emit(self, record):
            super().emit(record)
            LOG_ENTRIES.labels(level=record.levelname.lower()).inc()


    # 为FastAPI应用添加监控中间件
    class MonitoringMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope['type'] != 'http':
                return await self.app(scope, receive, send)

            # 记录请求开始时间
            start_time = time.time()

            # 获取请求方法和路径
            method = scope['method']
            path = scope['path']

            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    status_code = message.get('status', 200)
                    # 记录请求指标
                    REQUEST_COUNT.labels(
                        method=method,
                        endpoint=path,
                        status=status_code
                    ).inc()

                    # 记录请求持续时间
                    duration = time.time() - start_time
                    REQUEST_DURATION.observe(duration)

                await send(message)

            # 获取请求大小
            headers = dict(scope.get('headers', []))
            content_length = headers.get(b'content-length')
            if content_length:
                try:
                    REQUEST_SIZE.observe(int(content_length))
                except ValueError:
                    pass  # 忽略无法转换的content-length值

            # 处理请求
            return await self.app(scope, receive, send_wrapper)


    # 健康检查端点
    def setup_health_check(app):
        # FastAPI中需要不同的健康检查实现
        from fastapi import FastAPI
        from fastapi.responses import Response

        @app.get('/health')
        def health_check():
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

        @app.get('/metrics')
        def metrics():
            from prometheus_client import generate_latest
            return Response(content=generate_latest(), media_type='text/plain; charset=utf-8')

except ImportError:
    Counter, Histogram, Gauge, Summary, generate_latest = None, None, None, None, None
    time = None


    # Prometheus客户端不可用时不启用监控
    class MonitoringMiddleware:
        def __init__(self, app):
            pass

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)


    def setup_health_check(app):
        from fastapi import FastAPI
        from fastapi.responses import Response

        @app.get('/health')
        def health_check():
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

        @app.get('/metrics')
        def metrics():
            # prometheus_client不可用，返回空响应
            return Response(content='Metrics not available', status_code=501, media_type='text/plain; charset=utf-8')

# 使用示例
if __name__ == "__main__":
    # 初始化优化的日志系统
    logger = init_optimized_logger()
    # 测试日志
    logger.info("应用启动")
    logger.warning("这是一个警告")
    logger.error("这是一个错误")

    logger.info("日志系统测试完成")


# ==================== 日志工具函数 ====================

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取命名日志器
    
    Args:
        name: 日志器名称（通常是模块名）
        level: 日志级别
        
    Returns:
        配置好的 Logger 对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs):
    """
    记录性能日志
    
    Args:
        logger: 日志器
        operation: 操作名称
        duration: 耗时（秒）
        **kwargs: 额外信息
    """
    extra_data = {
        'operation': operation,
        'duration_ms': round(duration * 1000, 2),
        **kwargs
    }

    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        '', 0, '', (), None
    )
    record.extra_data = extra_data
    logger.handle(record)


def log_request(logger: logging.Logger, method: str, path: str, status: int,
                duration: float, user_id: Optional[int] = None, **kwargs):
    """
    记录 HTTP 请求日志
    
    Args:
        logger: 日志器
        method: HTTP 方法
        path: 请求路径
        status: 响应状态码
        duration: 处理时间（秒）
        user_id: 用户 ID（可选）
        **kwargs: 额外信息
    """
    extra_data = {
        'type': 'http_request',
        'method': method,
        'path': path,
        'status': status,
        'duration_ms': round(duration * 1000, 2),
    }

    if user_id:
        extra_data['user_id'] = user_id

    extra_data.update(kwargs)

    # 根据状态码选择日志级别
    level = logging.WARNING if status >= 400 else logging.INFO

    record = logger.makeRecord(
        logger.name,
        level,
        '', 0, f"{method} {path} {status}", (), None
    )
    record.extra_data = extra_data
    logger.handle(record)


def log_database_query(logger: logging.Logger, query_type: str, table: str,
                       duration: float, rows_affected: int = 0, **kwargs):
    """
    记录数据库查询日志
    
    Args:
        logger: 日志器
        query_type: 查询类型 (SELECT, INSERT, UPDATE, DELETE)
        table: 表名
        duration: 查询耗时（秒）
        rows_affected: 影响行数
        **kwargs: 额外信息
    """
    extra_data = {
        'type': 'db_query',
        'query_type': query_type,
        'table': table,
        'duration_ms': round(duration * 1000, 2),
        'rows_affected': rows_affected,
    }

    extra_data.update(kwargs)

    # 慢查询警告（超过 100ms）
    level = logging.WARNING if duration > 0.1 else logging.DEBUG

    record = logger.makeRecord(
        logger.name,
        level,
        '', 0, f"{query_type} {table} ({duration * 1000:.2f}ms)", (), None
    )
    record.extra_data = extra_data
    logger.handle(record)


def log_security_event(logger: logging.Logger, event_type: str, severity: str,
                       source_ip: str, details: dict, **kwargs):
    """
    记录安全事件日志
    
    Args:
        logger: 日志器
        event_type: 事件类型 (login_failed, sql_injection, xss_attempt等)
        severity: 严重程度 (low, medium, high, critical)
        source_ip: 来源 IP
        details: 详细信息
        **kwargs: 额外信息
    """
    extra_data = {
        'type': 'security_event',
        'event_type': event_type,
        'severity': severity,
        'source_ip': source_ip,
        'details': details,
    }

    extra_data.update(kwargs)

    # 根据严重程度选择日志级别
    severity_levels = {
        'low': logging.INFO,
        'medium': logging.WARNING,
        'high': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = severity_levels.get(severity, logging.WARNING)

    record = logger.makeRecord(
        logger.name,
        level,
        '', 0, f"Security Event: {event_type} [{severity}]", (), None
    )
    record.extra_data = extra_data
    logger.handle(record)


def analyze_log_file(log_path: str, top_n: int = 10) -> dict:
    """
    分析日志文件，提取统计信息
    
    Args:
        log_path: 日志文件路径
        top_n: 显示前 N 条记录
        
    Returns:
        分析结果字典
    """
    from collections import Counter

    stats = {
        'total_lines': 0,
        'level_counts': Counter(),
        'error_messages': [],
        'slow_operations': [],
    }

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                stats['total_lines'] += 1

                try:
                    log_entry = json.loads(line.strip())
                    level = log_entry.get('level', 'I')
                    stats['level_counts'][level] += 1

                    # 收集错误消息
                    if level in ['E', 'C']:
                        stats['error_messages'].append({
                            'msg': log_entry.get('msg', ''),
                            'loc': log_entry.get('loc', ''),
                            'ts': log_entry.get('ts', '')
                        })

                    # 收集慢操作
                    data = log_entry.get('data', {})
                    if isinstance(data, dict):
                        duration_ms = data.get('duration_ms', 0)
                        if duration_ms > 100:  # 超过 100ms
                            stats['slow_operations'].append({
                                'operation': data.get('operation', 'unknown'),
                                'duration_ms': duration_ms,
                                'ts': log_entry.get('ts', '')
                            })
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return {'error': f'File not found: {log_path}'}

    # 排序并截取
    stats['error_messages'] = stats['error_messages'][-top_n:]
    stats['slow_operations'] = sorted(
        stats['slow_operations'],
        key=lambda x: x['duration_ms'],
        reverse=True
    )[:top_n]

    return stats
