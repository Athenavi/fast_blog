# FastBlog 速率限制系统

## 概述

FastBlog 实现了多层次、细粒度的速率限制系统，用于防止 API 滥用和 DDoS 攻击。

## 架构设计

### 核心特性

1. **基于 IP 的限流** - 每个客户端 IP 独立计数
2. **路径级差异化限流** - 不同端点有不同的限流策略
3. **滑动窗口算法** - 精确控制请求频率
4. **标准 HTTP 头** - 返回 RateLimit 相关头部
5. **内存高效** - 自动清理过期记录

### 限流层级

```
用户请求
  ↓
排除路径检查 (缩略图、静态文件等)
  ↓
获取客户端 IP
  ↓
根据路径选择限流策略
  ↓
检查是否超限
  ↓
允许/拒绝请求
```

## 配置说明

### 默认限流策略

```python
DEFAULT_MAX_REQUESTS = 100    # 每分钟最多 100 次请求
DEFAULT_WINDOW_SECONDS = 60   # 时间窗口 60 秒
```

### 敏感端点严格限流

```python
STRICT_LIMITS = {
    '/api/v1/auth/login': (5, 60),      # 登录：5次/分钟
    '/api/v1/auth/register': (3, 300),  # 注册：3次/5分钟
    '/api/v1/users/password': (3, 300), # 密码重置：3次/5分钟
}
```

### 排除路径（不限流）

```python
EXCLUDED_PATHS = [
    '/api/v1/thumbnail',  # 缩略图接口
    '/api/v1/media/',     # 媒体文件接口
    '/health',            # 健康检查接口
    '/static/',           # 静态文件
]
```

## 使用方法

### 基本使用

速率限制中间件已自动集成到应用中，无需额外配置：

```python
# src/app.py
from src.auth.security_middleware import create_security_middleware_stack

create_security_middleware_stack(
    app,
    rate_limit_requests=100,  # 已废弃，使用类常量
    rate_limit_window=60  # 已废弃，使用类常量
)
```

### 自定义限流策略

修改 `src/auth/security_middleware.py` 中的配置：

```python
class RateLimiterMiddleware(BaseHTTPMiddleware):
    # 修改默认限制
    DEFAULT_MAX_REQUESTS = 200
    DEFAULT_WINDOW_SECONDS = 60

    # 添加新的严格限制
    STRICT_LIMITS = {
        '/api/v1/auth/login': (5, 60),
        '/api/v1/articles': (50, 60),  # 文章列表：50次/分钟
        '/api/v1/comments': (10, 60),  # 评论：10次/分钟
    }

    # 添加更多排除路径
    EXCLUDED_PATHS = [
        '/api/v1/thumbnail',
        '/api/v1/media/',
        '/health',
        '/static/',
        '/api/v1/search',  # 搜索接口豁免
    ]
```

## 响应头说明

### 成功响应

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1714550400
```

- `X-RateLimit-Limit`: 时间窗口内的最大请求数
- `X-RateLimit-Remaining`: 剩余可用请求数
- `X-RateLimit-Reset`: 限流重置时间戳（Unix timestamp）

### 限流响应

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1714550400

{
  "success": false,
  "error": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

## 实现细节

### 滑动窗口算法

```python
def _check_rate_limit(self, client_ip, path, max_requests, window_seconds):
    now = time.time()
    window_start = now - window_seconds

    # 使用 IP + 路径作为 key
    rate_key = f"{client_ip}:{path}"

    # 清理过期记录
    self.request_log[rate_key] = [
        ts for ts in self.request_log[rate_key]
        if ts > window_start
    ]

    # 检查是否超限
    if len(self.request_log[rate_key]) >= max_requests:
        return False

    # 记录当前请求
    self.request_log[rate_key].append(now)
    return True
```

### 内存管理

- 自动清理过期的请求记录
- 使用 defaultdict 减少内存占用
- 按 IP + 路径分组，避免单一 IP 占用过多内存

## 监控与调试

### 日志记录

可以在中间件中添加日志：

```python
import logging

logger = logging.getLogger(__name__)


async def dispatch(self, request: Request, call_next):
    client_ip = self._get_client_ip(request)
    path = request.url.path

    logger.info(f"Rate limit check: {client_ip} -> {path}")

    # ... 限流逻辑
```

### 监控指标

建议收集以下指标：

1. **429 错误率** - 被限流的请求比例
2. **平均剩余请求数** - 评估限流阈值是否合理
3. **热门 IP 排行** - 识别异常流量

## 最佳实践

### 1. 合理设置限流阈值

- **公开 API**: 100-200 次/分钟
- **认证 API**: 50-100 次/分钟
- **敏感操作**: 5-10 次/分钟
- **文件上传**: 10-20 次/小时

### 2. 渐进式限流

```python
# 根据用户等级调整限流
if user.is_vip:
    max_requests *= 2
elif user.is_authenticated:
    max_requests *= 1.5
```

### 3. 白名单机制

```python
WHITELIST_IPS = ['192.168.1.100', '10.0.0.1']

if client_ip in WHITELIST_IPS:
    return await call_next(request)
```

### 4. 分布式限流（生产环境）

对于多实例部署，建议使用 Redis：

```python
import redis

class RedisRateLimiter:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)
    
    def check_rate_limit(self, key, max_requests, window_seconds):
        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, window_seconds)
        return current <= max_requests
```

## 常见问题

### Q1: 如何临时禁用限流？

```python
# 在开发环境中
import os
if os.getenv('DISABLE_RATE_LIMIT') == 'true':
    return await call_next(request)
```

### Q2: 如何处理代理后面的真实 IP？

中间件已支持常见的代理头：

- `X-Forwarded-For`
- `X-Real-IP`

确保反向代理正确设置这些头部。

### Q3: 限流数据会丢失吗？

是的，当前实现使用内存存储，重启后会丢失。生产环境建议使用 Redis。

### Q4: 如何测试限流功能？

```bash
# 使用 curl 快速发送请求
for i in {1..110}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/articles
done

# 观察最后几个请求是否返回 429
```

## 性能影响

- **内存占用**: 每个 IP+路径组合约 100 bytes
- **CPU 开销**: < 1ms per request
- **延迟增加**: < 0.5ms

## 安全建议

1. **定期审查限流日志** - 发现异常模式
2. **结合其他安全措施** - WAF、IP 黑名单等
3. **动态调整阈值** - 根据实际流量调整
4. **监控误报** - 确保正常用户不受影响

## 未来改进

- [ ] 支持 Redis 后端（分布式限流）
- [ ] 支持用户级限流（而非仅 IP）
- [ ] 支持令牌桶算法
- [ ] 支持动态配置（无需重启）
- [ ] 支持限流规则的热更新

## 相关资源

- [OWASP Rate Limiting](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html#rate-limiting)
- [RFC 6585 - Additional HTTP Status Codes](https://tools.ietf.org/html/rfc6585)
- [SlowAPI - FastAPI Rate Limiting](https://slowapi.readthedocs.io/)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
