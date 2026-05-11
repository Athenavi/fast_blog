"""
维护模式中间件 - 拦截请求并返回维护页面
Debug查询日志中间件 - 记录SQL查询性能
"""
import time
from fastapi import Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from shared.services.maintenance_mode import maintenance_service
from django.conf import settings
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """维护模式中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = request.client.host if request.client else None
        
        # 检查是否处于维护模式
        if maintenance_service.is_maintenance_mode(client_ip):
            # 获取配置
            config = maintenance_service.load_config()
            message = config.get('message', '系统正在维护中，请稍后访问')
            retry_after = config.get('retry_after', 3600)
            
            # 检查是否为API请求
            if request.url.path.startswith('/api/') or request.url.path.startswith('/v1/'):
                # API请求返回JSON
                return JSONResponse(
                    status_code=503,
                    content={
                        "success": False,
                        "error": "Service Unavailable",
                        "message": message,
                        "retry_after": retry_after
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "Content-Type": "application/json"
                    }
                )
            
            # 检查是否为静态资源（允许访问）
            static_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf']
            path_lower = request.url.path.lower()
            
            if any(path_lower.endswith(ext) for ext in static_extensions):
                # 静态资源直接放行
                return await call_next(request)
            
            # 其他请求返回HTML维护页面
            html_content = self._generate_maintenance_page(message)
            return HTMLResponse(
                content=html_content,
                status_code=503,
                headers={
                    "Retry-After": str(retry_after),
                    "Content-Type": "text/html; charset=utf-8"
                }
            )
        
        # 非维护模式，继续处理请求
        return await call_next(request)
    
    def _generate_maintenance_page(self, message: str) -> str:
        """生成维护页面HTML"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统维护中</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 20px;
            padding: 60px 40px;
            max-width: 600px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        
        .icon {{
            font-size: 80px;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #333;
            font-size: 32px;
            margin-bottom: 20px;
            font-weight: 700;
        }}
        
        .message {{
            color: #666;
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 30px;
        }}
        
        .info {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            border-radius: 8px;
            text-align: left;
            margin-top: 30px;
        }}
        
        .info p {{
            color: #666;
            font-size: 14px;
            margin: 5px 0;
        }}
        
        .info strong {{
            color: #333;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 40px 20px;
            }}
            
            h1 {{
                font-size: 24px;
            }}
            
            .message {{
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔧</div>
        <h1>系统维护中</h1>
        <p class="message">{message}</p>
        <div class="info">
            <p><strong>提示：</strong>我们正在对系统进行升级维护，以提供更好的服务体验。</p>
            <p><strong>预计恢复时间：</strong>请稍后重试</p>
            <p><strong>如有疑问：</strong>请联系网站管理员</p>
        </div>
    </div>
</body>
</html>"""


class QueryLoggingMiddleware(BaseHTTPMiddleware):
    """SQL查询日志中间件 - 记录慢查询和N+1问题"""
    
    async def dispatch(self, request: Request, call_next):
        # 仅在Debug模式下工作
        if not getattr(settings, 'LOG_QUERIES', False) and not getattr(settings, 'SAVEQUERIES', False):
            return await call_next(request)
        
        start_time = time.time()
        
        # 重置查询日志
        if hasattr(connection, 'queries'):
            connection.queries_log.clear()
        
        response = await call_next(request)
        
        elapsed_time = time.time() - start_time
        
        # 记录查询信息
        if hasattr(connection, 'queries'):
            queries = connection.queries
            query_count = len(queries)
            
            # 检测慢查询 (>100ms)
            slow_queries = []
            for query in queries:
                query_time = float(query.get('time', 0))
                if query_time > 0.1:  # 100ms
                    slow_queries.append({
                        'sql': query.get('sql', '')[:200],
                        'time': query_time,
                    })
            
            # 检测N+1查询 (相同查询模式出现多次)
            query_patterns = {}
            for query in queries:
                sql = query.get('sql', '')
                # 简化SQL以检测模式
                simplified = self._simplify_query(sql)
                if simplified:
                    query_patterns[simplified] = query_patterns.get(simplified, 0) + 1
            
            n_plus_one = {k: v for k, v in query_patterns.items() if v > 5}
            
            # 记录日志
            if settings.LOG_QUERIES:
                logger.info(
                    f"Request: {request.method} {request.url.path} | "
                    f"Time: {elapsed_time:.3f}s | Queries: {query_count} | "
                    f"Slow: {len(slow_queries)} | N+1: {len(n_plus_one)}"
                )
                
                if slow_queries:
                    logger.warning(f"Slow queries detected: {slow_queries}")
                
                if n_plus_one:
                    logger.warning(f"Potential N+1 queries: {n_plus_one}")
            
            # 添加响应头(Debug信息)
            if settings.SHOW_ERRORS and getattr(settings, 'DEBUG', False):
                response.headers['X-Query-Count'] = str(query_count)
                response.headers['X-Request-Time'] = f"{elapsed_time:.3f}s"
                if slow_queries:
                    response.headers['X-Slow-Queries'] = str(len(slow_queries))
        
        return response
    
    def _simplify_query(self, sql: str) -> str:
        """简化SQL查询以检测模式"""
        import re
        if not sql:
            return ''
        
        # 移除具体值，保留结构
        simplified = re.sub(r"'[^']*'", "'?'", sql)
        simplified = re.sub(r'\b\d+\b', '?', simplified)
        
        # 只保留SELECT/UPDATE/DELETE/INSERT关键字前的部分
        match = re.match(r'(SELECT|UPDATE|DELETE|INSERT)\s+', simplified, re.IGNORECASE)
        if match:
            return match.group(0).upper() + simplified[match.end():match.end()+50]
        
        return simplified[:100]
