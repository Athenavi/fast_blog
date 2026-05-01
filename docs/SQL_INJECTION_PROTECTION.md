# SQL 注入防护系统

## 概述

FastBlog 实现了多层次的 SQL 注入防护系统，包括请求过滤、参数化查询和审计日志。

## 防护架构

### 三层防护体系

```
用户请求
  ↓
第1层: SQL 注入过滤中间件 (请求级别)
  ↓
第2层: ORM 参数化查询 (数据库级别)
  ↓
第3层: 数据库权限控制 (系统级别)
```

## 第1层：SQL 注入过滤中间件

### 功能特性

1. **实时检测** - 拦截包含 SQL 注入模式的请求
2. **多维度检测** - 检查查询参数和请求体
3. **分级响应** - 区分普通和严重威胁
4. **审计日志** - 记录所有注入尝试
5. **智能排除** - 避免误报（如搜索接口）

### 检测模式

#### SQL 关键字检测

```python
SELECT, INSERT, UPDATE, DELETE, DROP, UNION, ALTER, CREATE, EXEC, EXECUTE
```

#### SQL 注释检测

```python
--, #, /*, */
```

#### 逻辑注入检测

```python
OR 1=1
AND 1=1
OR 'a'='a'
```

#### 危险函数检测

```python
CONCAT, CHAR, CHR, ASCII, SUBSTRING, MID
LOAD_FILE, INTO OUTFILE, INTO DUMPFILE
```

#### 时间盲注检测

```python
SLEEP, BENCHMARK, WAITFOR DELAY
```

#### 错误注入检测

```python
EXTRACTVALUE, UPDATEXML, XMLTYPE
```

### 配置说明

```python
class SQLInjectionFilterMiddleware(BaseHTTPMiddleware):
    # 排除的路径（避免误报）
    EXCLUDED_PATHS = [
        '/api/v1/search',  # 搜索接口可能包含特殊字符
    ]

    # 启用/禁用日志记录
    def __init__(self, app, enable_logging: bool = True):
        self.enable_logging = enable_logging
```

### 响应示例

**检测到 SQL 注入:**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "Invalid request parameters (SQL injection detected)",
  "pattern_matched": "(\\b(DROP|TRUNCATE|ALTER)\\b)"
}
```

**日志输出:**

```
WARNING: SQL Injection attempt detected from 192.168.1.100
  Method: POST
  Path: /api/v1/auth/login
  Source: request_body
  Pattern: (\b(DROP|TRUNCATE|ALTER)\b)
  Critical: True
```

## 第2层：ORM 参数化查询

### 最佳实践

#### ✅ 正确：使用参数化查询

```python
from sqlalchemy import select

# SQLAlchemy ORM - 自动参数化
async def get_user_by_id(session, user_id: int):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# 原生 SQL - 使用参数
async def search_articles(session, keyword: str):
    query = text("SELECT * FROM articles WHERE title LIKE :keyword")
    result = await session.execute(query, {"keyword": f"%{keyword}%"})
    return result.fetchall()
```

#### ❌ 错误：字符串拼接

```python
# 绝对禁止！
query = f"SELECT * FROM users WHERE username = '{username}'"
query = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
```

### 常见场景示例

#### 1. 用户认证

```python
# ✅ 正确
async def authenticate(session, username: str, password: str):
    result = await session.execute(
        select(User).where(
            and_(
                User.username == username,
                User.password_hash == hash_password(password)
            )
        )
    )
    return result.scalar_one_or_none()

# ❌ 错误 - SQL 注入漏洞
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
```

#### 2. 文章搜索

```python
# ✅ 正确
async def search_articles(session, keyword: str, page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    query = text("""
        SELECT * FROM articles 
        WHERE title LIKE :keyword OR content LIKE :keyword
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await session.execute(
        query,
        {
            "keyword": f"%{keyword}%",
            "limit": per_page,
            "offset": offset
        }
    )
    return result.fetchall()
```

#### 3. 动态排序

```python
# ✅ 正确 - 白名单验证
ALLOWED_SORT_FIELDS = ['created_at', 'updated_at', 'title', 'views']

async def get_articles(session, sort_by: str = 'created_at', order: str = 'DESC'):
    # 验证排序字段
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = 'created_at'
    
    # 验证排序方向
    order = order.upper()
    if order not in ['ASC', 'DESC']:
        order = 'DESC'
    
    # 构建查询
    from sqlalchemy import desc, asc
    query = select(Article)
    
    if order == 'DESC':
        query = query.order_by(desc(getattr(Article, sort_by)))
    else:
        query = query.order_by(asc(getattr(Article, sort_by)))
    
    result = await session.execute(query)
    return result.scalars().all()
```

## 第3层：数据库权限控制

### 最小权限原则

```sql
-- 创建专用数据库用户
CREATE USER 'fastblog_app'@'localhost' IDENTIFIED BY 'strong_password';

-- 仅授予必要的权限
GRANT SELECT, INSERT, UPDATE, DELETE ON fastblog.* TO 'fastblog_app'@'localhost';

-- 禁止危险操作
REVOKE DROP, ALTER, CREATE, TRIGGER ON fastblog.* FROM 'fastblog_app'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;
```

### 权限矩阵

| 操作     | 应用用户 | 管理员用户 |
|--------|------|-------|
| SELECT | ✅    | ✅     |
| INSERT | ✅    | ✅     |
| UPDATE | ✅    | ✅     |
| DELETE | ✅    | ✅     |
| DROP   | ❌    | ✅     |
| ALTER  | ❌    | ✅     |
| CREATE | ❌    | ✅     |
| GRANT  | ❌    | ✅     |

## 审计与监控

### 运行审计测试

```bash
# 基本审计
python scripts/sql_injection_audit.py

# 指定服务器地址
python scripts/sql_injection_audit.py http://your-server.com
```

### 审计内容

1. **基本注入测试** - 10+ 常见 payload
2. **POST 请求测试** - 表单注入测试
3. **严重威胁测试** - DROP、文件操作等
4. **生成详细报告** - JSON 格式保存

### 监控指标

建议收集以下指标：

1. **SQL 注入拦截次数** - 按小时/天统计
2. **来源 IP 分布** - 识别攻击源
3. **payload 类型分布** - 了解攻击手法
4. **误报率** - 优化过滤规则

## 安全建议

### 1. 输入验证

```python
from pydantic import BaseModel, validator

class ArticleCreate(BaseModel):
    title: str
    content: str
    
    @validator('title')
    def validate_title(cls, v):
        # 长度限制
        if len(v) > 255:
            raise ValueError('Title too long')
        
        # 拒绝危险字符
        dangerous_chars = [';', '--', '/*', '*/']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'Dangerous character detected: {char}')
        
        return v
```

### 2. 错误处理

```python
# ✅ 正确 - 不暴露内部错误
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# ❌ 错误 - 暴露敏感信息
return JSONResponse(
    status_code=500,
    content={"error": str(exc), "sql": query}  # 泄露 SQL 语句！
)
```

### 3. 定期更新

- 每月审查 SQL 注入日志
- 每季度更新检测规则
- 每年进行渗透测试

## 常见问题

### Q1: 如何避免误报？

对于可能包含特殊字符的接口（如搜索），添加到排除列表：

```python
EXCLUDED_PATHS = [
    '/api/v1/search',
    '/api/v1/articles/filter',
]
```

并在代码层面使用参数化查询确保安全。

### Q2: 性能影响如何？

- 正则表达式匹配：< 1ms per request
- 对整体性能影响：< 0.1%
- 可以通过缓存优化

### Q3: 能否绕过防护？

理论上任何防护都可能被绕过，因此采用多层防护：

1. 中间件过滤
2. ORM 参数化
3. 数据库权限

即使某一层被绕过，其他层仍能提供保护。

### Q4: 如何处理合法的 SQL 关键字？

如果业务需要（如技术博客），可以：

1. 在特定端点禁用中间件
2. 使用更精确的正则表达式
3. 在后端进行二次验证

## 测试用例

### 测试脚本

```python
import requests

def test_sql_injection_protection():
    """测试 SQL 注入防护"""
    base_url = "http://localhost:9421"
    
    # 测试 payload
    payloads = [
        "1' OR '1'='1",
        "admin'--",
        "'; DROP TABLE users--",
        "1' AND SLEEP(5)--",
    ]
    
    for payload in payloads:
        response = requests.get(
            f"{base_url}/api/v1/search",
            params={"q": payload}
        )
        
        assert response.status_code == 400, f"Failed to block: {payload}"
        print(f"✅ Blocked: {payload}")
    
    print("All tests passed!")

test_sql_injection_protection()
```

## 相关资源

- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [SQLMap - 自动化测试工具](https://sqlmap.org/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/core/tutorial.html#using-textual-sql)

## 未来改进

- [ ] 机器学习检测异常模式
- [ ] 实时威胁情报集成
- [ ] 自动化规则更新
- [ ] Web Application Firewall (WAF) 集成

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
