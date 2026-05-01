# 安全加固报告

## 📋 概述

FastBlog 已经实现了多层次的安全防护体系，涵盖 OWASP Top 10 的主要威胁。本报告详细说明现有的安全措施和使用方法。

---

## 🛡️ 已实现的安全功能

### 1. XSS (跨站脚本) 防护 ✅

**实现位置**:

- `src/auth/security_middleware.py` - XSSFilterMiddleware
- `plugins/security-guard/plugin.py` - SecurityGuardPlugin

**防护特性**:

- ✅ 检测 `<script>` 标签
- ✅ 检测 JavaScript/VBScript 协议
- ✅ 检测事件处理器 (onclick, onerror 等)
- ✅ 检测危险标签 (iframe, object, embed 等)
- ✅ 检测 SVG/MathML XSS
- ✅ 检测 CSS 表达式
- ✅ 检测编码绕过尝试
- ✅ 智能排除（避免误报）

**配置示例**:

```python
# src/auth/security_middleware.py
class XSSFilterMiddleware(BaseHTTPMiddleware):
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript\s*:',
        r'on\w+\s*=\s*["\']',
        # ... 更多模式
    ]
```

**使用方法**:
中间件已在 `src/app.py` 中自动加载，无需额外配置。

---

### 2. CSRF (跨站请求伪造) 防护 ✅

**实现位置**: `src/auth/security_middleware.py` - CSRFProtectionMiddleware

**防护特性**:

- ✅ Token 验证机制
- ✅ 一次性 Token（使用后立即删除）
- ✅ 支持 X-CSRF-Token 和 X-XSRF-TOKEN header
- ✅ API 请求可通过 Authorization header 跳过检查
- ✅ 基于 Redis/Cache 存储 Token

**工作流程**:

```
1. 客户端请求 CSRF Token
2. 服务器生成唯一 Token 并存入 Cache
3. 客户端在请求头中携带 Token
4. 服务器验证 Token 有效性
5. 验证成功后删除 Token（一次性使用）
```

**前端使用示例**:

```typescript
// 获取 CSRF Token
const response = await fetch('/api/v1/csrf-token')
const {csrf_token} = await response.json()

// 在请求中使用
fetch('/api/v1/articles', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': csrf_token,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
})
```

---

### 3. 速率限制 (Rate Limiting) ✅

**实现位置**:

- `src/auth/security_middleware.py` - RateLimiterMiddleware
- `plugins/security-guard/plugin.py` - 插件级速率限制
- `plugins/firewall-rules/` - 防火墙级速率限制

**防护特性**:

- ✅ 基于 IP 的请求频率控制
- ✅ 不同端点的差异化限流策略
- ✅ 可配置的请求数和時間窗口
- ✅ 返回剩余请求数信息
- ✅ 支持路径级别的细粒度控制

**默认配置**:

```python
# src/app.py
create_security_middleware_stack(
    app,
    rate_limit_requests=100,  # 每分钟 100 次请求
    rate_limit_window=60  # 60 秒时间窗口
)
```

**自定义配置**:

```python
# 登录接口更严格的限制
RATE_LIMIT_RULES = {
    '/api/v1/auth/login': (5, 60),  # 5次/分钟
    '/api/v1/auth/register': (3, 300),  # 3次/5分钟
    '/api/v1/articles': (100, 60),  # 100次/分钟
}
```

**响应头**:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

### 4. SQL 注入防护 ✅

**实现位置**:

- `src/auth/security_middleware.py` - SQLInjectionFilterMiddleware
- `docs/SQL_INJECTION_PROTECTION.md` - 详细文档

**三层防护体系**:

```
用户请求
  ↓
第1层: SQL 注入过滤中间件 (请求级别)
  ↓
第2层: ORM 参数化查询 (数据库级别)
  ↓
第3层: 数据库权限控制 (系统级别)
```

**检测模式**:

- ✅ SQL 关键字 (SELECT, INSERT, UPDATE, DELETE, DROP 等)
- ✅ SQL 注释 (--, #, /*, */)
- ✅ 逻辑注入 (OR 1=1, AND 1=1)
- ✅ 危险函数 (CONCAT, CHAR, LOAD_FILE 等)
- ✅ 时间盲注 (SLEEP, BENCHMARK)
- ✅ 错误注入 (EXTRACTVALUE, UPDATEXML)

**审计日志**:

```python
# 记录所有注入尝试
{
    'timestamp': '2026-05-01 12:00:00',
    'ip': '192.168.1.100',
    'path': '/api/v1/articles',
    'method': 'GET',
    'pattern': 'UNION SELECT',
    'severity': 'critical',
    'payload': 'id=1 UNION SELECT * FROM users'
}
```

**安全查询示例**:

```python
# ✅ 正确 - 使用参数化查询
async def get_article(session, article_id: int):
    result = await session.execute(
        select(Article).where(Article.id == article_id)
    )
    return result.scalar_one_or_none()


# ❌ 错误 - SQL 注入漏洞
query = f"SELECT * FROM articles WHERE id={article_id}"
```

---

### 5. CORS (跨域资源共享) 配置 ✅

**实现位置**:

- `src/app.py` - FastAPI CORS 中间件
- `django_blog/settings.py` - Django CORS 配置

**配置示例**:

```env
# .env 文件
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**生产环境最佳实践**:

```python
# src/app.py
allow_origins = os.getenv('CORS_ORIGINS', '').split(',')
allow_origins = [origin.strip() for origin in allow_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,  # 严格限制允许的源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Cookie"],
    expose_headers=["Content-Length", "X-Total-Count"],
)
```

**⚠️ 安全提示**:

- ❌ 不要使用 `*` 通配符
- ✅ 只添加信任的域名
- ✅ 明确指定允许的方法和头部

---

### 6. 安全响应头 ✅

**实现位置**: `plugins/security-guard/security_headers.py`

**已配置的安全头**:

```python
security_headers = {
    # 防止点击劫持
    'X-Frame-Options': 'DENY',

    # 防止 MIME 类型嗅探
    'X-Content-Type-Options': 'nosniff',

    # XSS 保护
    'X-XSS-Protection': '1; mode=block',

    # 引用策略
    'Referrer-Policy': 'strict-origin-when-cross-origin',

    # 权限策略
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}
```

**可选配置**:

```python
# HSTS (HTTP Strict Transport Security)
hsts_enabled = True
hsts_max_age = 31536000  # 1年
hsts_include_subdomains = True

# CSP (Content Security Policy)
csp_policy = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline'",
    'style-src': "'self' 'unsafe-inline'",
    'img-src': "'self' data: https:",
}
```

---

### 7. 认证与授权 ✅

**实现位置**: `src/utils/security/security.py`

**功能特性**:

- ✅ JWT Token 认证
- ✅ 基于角色的访问控制 (RBAC)
- ✅ 权限依赖注入
- ✅ 密码哈希 (bcrypt)
- ✅ Token 过期管理

**角色定义**:

```python
class RoleEnum(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
```

**使用示例**:

```python
# 需要管理员权限
@router.post("/articles")
async def create_article(
        request: Request,
        current_user=Depends(permission_required([ADMIN_ROLE]))
):
    # 只有管理员可以创建文章
    pass


# 需要特定角色
@router.get("/admin/dashboard")
async def admin_dashboard(
        request: Request,
        current_user=Depends(role_required(RoleEnum.ADMIN))
):
    # 只有管理员可以访问
    pass
```

---

### 8. 文件上传安全 ✅

**实现位置**: `django_blog/settings.py`

**安全措施**:

- ✅ 文件大小限制 (默认 60MB)
- ✅ 文件类型白名单
- ✅ 存储配额管理
- ✅ 文件名 sanitization
- ✅ 病毒扫描集成 (可选)

**配置示例**:

```env
# .env 文件
UPLOAD_LIMIT=62914560  # 60MB
USER_FREE_STORAGE_LIMIT=536870912  # 512MB
```

**文件类型白名单**:

```python
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'application/msword']
```

---

### 9. 插件级安全防护 ✅

**实现位置**: `plugins/security-guard/`

**功能特性**:

- ✅ XSS 攻击防护
- ✅ CSRF 令牌验证
- ✅ 速率限制
- ✅ IP 黑名单/白名单
- ✅ 登录暴力破解防护
- ✅ SQL 注入检测
- ✅ 请求头安全检查
- ✅ 安全事件通知

**配置示例**:

```json
{
  "enable_xss_protection": true,
  "enable_rate_limiting": true,
  "rate_limit_requests": 60,
  "enable_ip_blacklist": true,
  "max_login_attempts": 5,
  "login_lockout_duration": 15,
  "enable_sql_injection_detection": true,
  "secure_headers": true
}
```

---

### 10. 防火墙规则 ✅

**实现位置**: `plugins/firewall-rules/`

**功能特性**:

- ✅ IP 黑名单/白名单
- ✅ 地理位置封锁
- ✅ 自动封禁 (Auto-ban)
- ✅ SQL 注入防护
- ✅ XSS 防护
- ✅ 路径遍历防护
- ✅ 请求日志记录

**配置示例**:

```json
{
  "enable_firewall": false,
  "enable_rate_limit": true,
  "rate_limit_requests": 100,
  "rate_limit_window": 60,
  "enable_ip_blacklist": true,
  "enable_auto_ban": true,
  "auto_ban_threshold": 50,
  "auto_ban_duration": 3600,
  "enable_sql_injection_protection": true,
  "enable_xss_protection": true
}
```

---

## 📊 安全监控与审计

### 1. 安全事件日志

**日志位置**: `logs/`

**日志格式**:

```json
{
  "timestamp": "2026-05-01T12:00:00Z",
  "level": "WARNING",
  "event_type": "xss_attempt",
  "ip": "192.168.1.100",
  "path": "/api/v1/articles",
  "details": "Detected <script> tag in request body"
}
```

### 2. 速率限制监控

**工具**: `scripts/rate_limit_monitor.py`

**使用方法**:

```bash
# 生成报告
python scripts/rate_limit_monitor.py report

# 实时监控
python scripts/rate_limit_monitor.py monitor --interval 60

# 发送警报
python scripts/rate_limit_monitor.py alert --threshold 10.0
```

### 3. 站点健康检查

**工具**: `shared/services/site_health.py`

**检查项目**:

- ✅ 安全配置检查
- ✅ CORS 配置验证
- ✅ 缓存系统状态
- ✅ 上传限制检查
- ✅ 数据库连接测试

**使用方法**:

```python
from shared.services.site_health import SiteHealthChecker

checker = SiteHealthChecker()
report = checker.generate_report(format='json')
print(report)
```

---

## 🔒 OWASP Top 10 覆盖情况

| OWASP 威胁                         | 防护措施             | 状态    |
|----------------------------------|------------------|-------|
| A01: Broken Access Control       | RBAC + JWT 认证    | ✅ 已覆盖 |
| A02: Cryptographic Failures      | bcrypt 密码哈希      | ✅ 已覆盖 |
| A03: Injection                   | SQL 注入过滤 + 参数化查询 | ✅ 已覆盖 |
| A04: Insecure Design             | 多层防护架构           | ✅ 已覆盖 |
| A05: Security Misconfiguration   | 安全头 + CORS 配置    | ✅ 已覆盖 |
| A06: Vulnerable Components       | 依赖扫描 (待实现)       | 🟡 部分 |
| A07: Authentication Failures     | 登录限制 + Token 管理  | ✅ 已覆盖 |
| A08: Software Integrity Failures | 插件签名 (待实现)       | 🟡 部分 |
| A09: Logging Failures            | 完整审计日志           | ✅ 已覆盖 |
| A10: SSRF                        | URL 白名单 (待实现)    | 🟡 部分 |

**覆盖率**: 70% (7/10 完全覆盖，3/10 部分覆盖)

---

## 🎯 安全最佳实践

### 1. 开发阶段

- ✅ 始终使用参数化查询
- ✅ 对所有用户输入进行验证和转义
- ✅ 实施最小权限原则
- ✅ 定期更新依赖包
- ✅ 使用环境变量管理敏感信息

### 2. 部署阶段

- ✅ 启用 HTTPS/TLS
- ✅ 配置 HSTS
- ✅ 设置合理的 CORS 策略
- ✅ 启用安全响应头
- ✅ 配置防火墙规则

### 3. 运维阶段

- ✅ 定期审查安全日志
- ✅ 监控异常流量
- ✅ 及时应用安全补丁
- ✅ 定期备份数据
- ✅ 进行安全审计

---

## 📚 相关文档

- [SQL 注入防护详解](../docs/SQL_INJECTION_PROTECTION.md)
- [速率限制监控](../docs/RATE_LIMIT_MONITORING.md)
- [配置指南](../docs/CONFIGURATION_GUIDE.md)
- [日志系统](../docs/LOGGING_SYSTEM.md)

---

## 🚀 未来改进计划

- [ ] Web Application Firewall (WAF) 集成
- [ ] 机器学习驱动的异常检测
- [ ] 实时威胁情报集成
- [ ] 自动化安全扫描
- [ ] 插件签名验证
- [ ] SSRF 防护增强
- [ ] 依赖漏洞扫描自动化

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
