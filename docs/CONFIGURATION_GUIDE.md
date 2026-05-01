# FastBlog 配置指南

本文档详细说明 FastBlog 的所有配置项，帮助你快速部署和定制系统。

## 快速开始

### 1. 创建配置文件

```bash
# 复制示例配置
cp .env_example .env

# 编辑配置
vim .env  # Linux/Mac
notepad .env  # Windows
```

### 2. 最小化配置（开发环境）

对于本地开发，只需修改以下必要配置：

```env
# 数据库
DB_PASSWORD=your_password

# 安全
SECRET_KEY=generate-a-random-string-here
JWT_SECRET_KEY=generate-another-random-string

# Redis
REDIS_HOST=localhost
```

生成随机密钥：

```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## 详细配置说明

### 数据库配置

#### PostgreSQL 连接

```env
DB_ENGINE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_NAME=fast_blog
DB_TABLE_PREFIX=fb_
```

**参数说明：**

- `DB_HOST`: 数据库服务器地址
- `DB_PORT`: 数据库端口（PostgreSQL 默认 5432）
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码 ⚠️ **生产环境必须修改**
- `DB_NAME`: 数据库名称
- `DB_TABLE_PREFIX`: 表名前缀（可选，用于多实例隔离）

#### 连接池配置

```env
DB_POOL_SIZE=20
DB_POOL_OVERFLOW=30
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=1800
```

**推荐配置：**

| 场景   | pool_size | max_overflow | 说明             |
|------|-----------|--------------|----------------|
| 开发环境 | 5         | 10           | 低并发            |
| 小型站点 | 20        | 30           | < 1000 DAU     |
| 中型站点 | 50        | 75           | 1000-10000 DAU |
| 大型站点 | 100       | 150          | > 10000 DAU    |

**计算公式：**

```
pool_size = CPU核心数 × 2
max_overflow = pool_size × 1.5
```

---

### 应用配置

#### 基本配置

```env
DOMAIN=http://localhost:9421
TITLE=FastBlog
DESCRIPTION=A modern, fast blog platform
KEYWORDS=blog, fast, modern
```

**参数说明：**

- `DOMAIN`: 网站域名，生产环境使用 HTTPS
- `TITLE`: 网站标题
- `DESCRIPTION`: 网站描述（SEO）
- `KEYWORDS`: 关键词（SEO）

#### 安全配置

```env
SECRET_KEY=your-secret-key-change-in-production
TIME_ZONE=Asia/Shanghai
ENVIRONMENT=development
DEBUG=True
```

**⚠️ 重要安全提示：**

1. **SECRET_KEY**:
    - 至少 32 字符
    - 使用随机生成的字符串
    - 生产环境绝对不能使用默认值

   生成方法：
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **DEBUG**:
    - 开发环境: `True`
    - 生产环境: `False` ⚠️
    - 开启 DEBUG 会暴露敏感信息

3. **ENVIRONMENT**:
    - `development`: 开发环境
    - `production`: 生产环境
    - `testing`: 测试环境

#### JWT 认证配置

```env
JWT_EXPIRATION_DELTA=86400
REFRESH_TOKEN_EXPIRATION_DELTA=604800
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
```

**参数说明：**

- `JWT_EXPIRATION_DELTA`: Access Token 过期时间（秒）
    - 默认: 86400 (24小时)
    - 建议: 短时效提高安全性

- `REFRESH_TOKEN_EXPIRATION_DELTA`: Refresh Token 过期时间（秒）
    - 默认: 604800 (7天)
    - 可根据需求调整

- `JWT_SECRET_KEY`: JWT 签名密钥 ⚠️ **必须与 SECRET_KEY 不同**

- `JWT_ALGORITHM`: 加密算法
    - 推荐: `HS256` 或 `RS256`

---

### Redis 配置

#### 基本配置

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
```

**参数说明：**

- `REDIS_HOST`: Redis 服务器地址
- `REDIS_PORT`: Redis 端口（默认 6379）
- `REDIS_DB`: 数据库编号（0-15）
- `REDIS_PASSWORD`: Redis 密码（如果有）
- `REDIS_MAX_CONNECTIONS`: 最大连接数

#### 缓存 TTL 配置

```env
CACHE_TTL_DEFAULT=600
CACHE_TTL_ARTICLES=3600
CACHE_TTL_USERS=1800
```

**推荐配置：**

| 数据类型 | TTL          | 说明     |
|------|--------------|--------|
| 默认缓存 | 600s (10分钟)  | 通用数据   |
| 文章列表 | 3600s (1小时)  | 变化较少   |
| 文章详情 | 1800s (30分钟) | 中等频率更新 |
| 用户信息 | 1800s (30分钟) | 较少变化   |
| 统计数据 | 300s (5分钟)   | 频繁更新   |

---

### 邮件配置

#### Gmail 配置

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=noreply@fastblog.com
MAIL_FROM_NAME=FastBlog
```

**Gmail 设置步骤：**

1. 启用两步验证
2. 生成应用专用密码：
    - 访问 https://myaccount.google.com/apppasswords
    - 选择"邮件"和应用
    - 复制生成的 16 位密码

#### QQ 邮箱配置

```env
MAIL_SERVER=smtp.qq.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_qq@qq.com
MAIL_PASSWORD=your_authorization_code
```

**QQ 邮箱设置步骤：**

1. 登录 QQ 邮箱
2. 设置 → 账户
3. 开启 POP3/SMTP 服务
4. 获取授权码

#### 163 邮箱配置

```env
MAIL_SERVER=smtp.163.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_163@163.com
MAIL_PASSWORD=your_authorization_code
```

---

### 文件存储配置

#### 上传限制

```env
UPLOAD_LIMIT=62914560
USER_FREE_STORAGE_LIMIT=536870912
```

**常用大小参考：**

| 大小     | 字节数        | 说明   |
|--------|------------|------|
| 10 MB  | 10485760   | 小图片  |
| 60 MB  | 62914560   | 默认限制 |
| 100 MB | 104857600  | 大图片  |
| 500 MB | 524288000  | 视频   |
| 1 GB   | 1073741824 | 大文件  |

#### S3/对象存储配置

```env
S3_ENABLED=True
S3_ENDPOINT_URL=
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=fastblog-media
S3_REGION=us-east-1
S3_USE_SSL=True
S3_SIGNATURE_VERSION=s3v4
```

**AWS S3 配置：**

```env
S3_ENDPOINT_URL=  # 留空
S3_REGION=us-east-1  # 根据你的区域修改
```

**Cloudflare R2 配置：**

```env
S3_ENDPOINT_URL=https://account-id.r2.cloudflarestorage.com
S3_REGION=auto
```

**DigitalOcean Spaces 配置：**

```env
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_REGION=nyc3
```

**MinIO 配置（自建）：**

```env
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION=us-east-1
S3_USE_SSL=False
```

#### CDN 配置

```env
CDN_ENABLED=False
CDN_URL=https://cdn.yourdomain.com
```

启用 CDN 后，所有静态资源将通过 CDN 分发，提升访问速度。

---

### CORS 配置

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

**开发环境：**

```env
CORS_ORIGINS=http://localhost:3000
```

**生产环境：**

```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**⚠️ 安全提示：**

- 不要使用 `*` 通配符
- 只添加信任的域名
- 多个域名用逗号分隔

---

### 日志配置

```env
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=3
```

**日志级别：**

| 级别       | 说明   | 使用场景     |
|----------|------|----------|
| DEBUG    | 调试信息 | 开发环境     |
| INFO     | 一般信息 | 生产环境（推荐） |
| WARNING  | 警告信息 | 需要注意的问题  |
| ERROR    | 错误信息 | 需要处理的错误  |
| CRITICAL | 严重错误 | 系统崩溃等    |

---

### 性能优化配置

```env
ARTICLES_PER_PAGE=10
SEARCH_RESULTS_PER_PAGE=20
COMMENTS_PER_PAGE=50
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

**速率限制建议：**

| 端点类型   | 请求数/分钟 | 说明      |
|--------|--------|---------|
| 公开 API | 100    | 文章列表、详情 |
| 认证 API | 10     | 登录、注册   |
| 管理 API | 50     | 后台操作    |
| 上传 API | 5      | 文件上传    |

---

### SEO 配置

```env
GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
GOOGLE_SITE_VERIFICATION=google-site-verification-code
BAIDU_ANALYTICS_ID=UM-XXXXXXXX-X
FACEBOOK_APP_ID=
TWITTER_CARD_TYPE=summary_large_image
```

**Google Analytics 4 设置：**

1. 创建 GA4 属性
2. 获取 Measurement ID (G-XXXXXXXXXX)
3. 填入配置

**Twitter Card 类型：**

- `summary`: 小卡片
- `summary_large_image`: 大图片卡片（推荐）

---

### 第三方服务集成

#### Sentry 错误追踪

```env
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_TRACES_SAMPLE_RATE=1.0
```

**设置步骤：**

1. 注册 Sentry 账号
2. 创建新项目
3. 复制 DSN
4. 配置采样率（0.0-1.0）

#### OpenAI API

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
```

用于 AI 写作助手、智能标签等功能。

#### 支付网关

**Stripe:**

```env
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**PayPal:**

```env
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_secret
PAYPAL_MODE=sandbox  # sandbox | live
```

---

### 其他配置

#### 用户注册

```env
ALLOW_REGISTRATION=True
EMAIL_VERIFICATION_REQUIRED=False
```

#### 国际化

```env
DEFAULT_LOCALE=zh_CN
SUPPORTED_LOCALES=zh_CN,en_US,ja_JP,ko_KR
```

**支持的语言代码：**

- `zh_CN`: 简体中文
- `en_US`: 英语（美国）
- `ja_JP`: 日语
- `ko_KR`: 韩语
- `fr_FR`: 法语
- `de_DE`: 德语
- `es_ES`: 西班牙语

#### 维护模式

```env
MAINTENANCE_MODE=False
MAINTENANCE_MESSAGE=网站正在维护中，请稍后访问
```

启用后，所有用户将看到维护页面（管理员除外）。

---

## 环境特定配置

### 开发环境 (.env.development)

```env
ENVIRONMENT=development
DEBUG=True
DB_HOST=localhost
DB_PASSWORD=dev_password
SECRET_KEY=dev-secret-key-not-for-production
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:3000
```

### 生产环境 (.env.production)

```env
ENVIRONMENT=production
DEBUG=False
DB_HOST=db.example.com
DB_PASSWORD=very-secure-password-here
SECRET_KEY=$(openssl rand -base64 32)
LOG_LEVEL=WARNING
CORS_ORIGINS=https://yourdomain.com
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 测试环境 (.env.testing)

```env
ENVIRONMENT=testing
DEBUG=True
DB_HOST=localhost
DB_NAME=fast_blog_test
DB_PASSWORD=test_password
SECRET_KEY=test-secret-key
LOG_LEVEL=ERROR
```

---

## 安全最佳实践

### 1. 密钥管理

✅ **正确做法：**

```env
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
```

❌ **错误做法：**

```env
SECRET_KEY=my-secret-key
JWT_SECRET_KEY=123456
```

### 2. 环境变量文件保护

```bash
# 确保 .env 不被提交到 Git
echo ".env" >> .gitignore

# 设置文件权限
chmod 600 .env
```

### 3. 数据库密码

- 使用强密码（至少 16 字符）
- 定期更换密码
- 不要在代码中硬编码

### 4. HTTPS

生产环境必须使用 HTTPS：

```env
DOMAIN=https://yourdomain.com
S3_USE_SSL=True
```

---

## 故障排查

### 问题 1: 数据库连接失败

**症状：**

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决：**

1. 检查 PostgreSQL 是否运行
2. 验证连接参数
3. 检查防火墙设置

```bash
# 测试连接
psql -h localhost -U postgres -d fast_blog
```

### 问题 2: Redis 连接失败

**症状：**

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决：**

1. 检查 Redis 是否运行
2. 验证端口和密码

```bash
# 测试连接
redis-cli ping
```

### 问题 3: 邮件发送失败

**症状：**

```
smtplib.SMTPAuthenticationError
```

**解决：**

1. 检查邮箱密码/授权码
2. 确认 SMTP 服务已开启
3. 检查防火墙

---

## 相关资源

- [API 使用示例](./API_EXAMPLES.md)
- [日志系统文档](./LOGGING_SYSTEM.md)
- [数据库索引优化](./DATABASE_INDEX_OPTIMIZATION.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
