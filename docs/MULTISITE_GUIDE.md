# 多站点支持使用指南

## 📋 概述

FastBlog 的多站点功能允许在单个安装中运行多个独立的博客站点，类似 WordPress Multisite。每个站点有独立的域名、主题、内容和配置，但共享用户系统和插件。

**核心特性**:

- ✅ 无限站点支持
- ✅ 基于域名或路径的站点路由
- ✅ 数据完全隔离（文章、分类、标签）
- ✅ 共享用户系统（跨站点登录）
- ✅ 独立主题和配置
- ✅ 统一管理界面
- ✅ 超级管理员面板

---

## 🏗️ 架构设计

### 数据模型

```
Sites (站点表)
├── id
├── name (站点名称)
├── slug (站点标识)
├── domain (域名，可选)
├── path (路径前缀，可选)
├── is_active (是否激活)
├── is_default (是否默认站点)
├── settings (JSON 配置)
├── theme (主题)
└── ...

Articles (文章表)
├── id
├── site_id (外键 → Sites)
├── title
├── content
└── ...

Categories (分类表)
├── id
├── site_id (外键 → Sites)
├── name
└── ...

Users (用户表 - 共享)
├── id
├── username
├── email
└── ... (无 site_id，全局共享)
```

### 站点识别策略

优先级顺序：

1. **域名匹配**: `example.com` → Site(domain='example.com')
2. **路径匹配**: `/site1/articles` → Site(path='/site1')
3. **默认站点**: is_default=true 的站点
4. **首个站点**: 第一个激活的站点

---

## 🚀 快速开始

### 1. 创建第一个站点

通过 API 创建站点：

```bash
curl -X POST "http://localhost:9421/api/v1/sites" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Blog",
    "slug": "myblog",
    "domain": "blog.example.com",
    "theme": "default",
    "language": "zh-CN",
    "settings": {
      "is_default": true
    }
  }'
```

### 2. 创建第二个站点

```bash
curl -X POST "http://localhost:9421/api/v1/sites" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Blog",
    "slug": "techblog",
    "domain": "tech.example.com",
    "theme": "modern-minimal",
    "language": "en"
  }'
```

### 3. 访问不同站点

**方式 1: 子域名**

- `blog.example.com` → My Blog
- `tech.example.com` → Tech Blog

**方式 2: 路径前缀**

- `example.com/myblog/articles` → My Blog
- `example.com/techblog/articles` → Tech Blog

---

## 📊 API 参考

### 1. 列出站点

**Endpoint**: `GET /api/v1/sites`

**Query Parameters**:

- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 20）

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "My Blog",
      "slug": "myblog",
      "domain": "blog.example.com",
      "path": "/",
      "is_active": true,
      "is_default": true,
      "theme": "default",
      "language": "zh-CN",
      "created_at": "2026-05-01T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 2,
    "pages": 1
  }
}
```

### 2. 创建站点

**Endpoint**: `POST /api/v1/sites`

**Request Body**:

```json
{
  "name": "Site Name",
  "slug": "site-slug",
  "domain": "example.com",
  "path": "/",
  "theme": "default",
  "language": "zh-CN",
  "timezone": "Asia/Shanghai",
  "title": "Site Title",
  "description": "Site Description",
  "keywords": "keyword1, keyword2",
  "admin_user_id": 1,
  "settings": {
    "is_default": false,
    "ssl_enabled": true
  }
}
```

**Response**:

```json
{
  "success": true,
  "message": "Site created successfully",
  "data": {
    "id": 2,
    "name": "Site Name",
    "slug": "site-slug"
  }
}
```

### 3. 获取站点详情

**Endpoint**: `GET /api/v1/sites/{site_id}`

**Response**:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "My Blog",
    "slug": "myblog",
    "domain": "blog.example.com",
    "path": "/",
    "is_active": true,
    "is_default": true,
    "theme": "default",
    "language": "zh-CN",
    "timezone": "Asia/Shanghai",
    "title": "My Blog Title",
    "description": "A blog about technology",
    "keywords": "tech, blog",
    "admin_user_id": 1,
    "settings": {},
    "full_url": "https://blog.example.com/",
    "created_at": "2026-05-01T12:00:00",
    "updated_at": "2026-05-01T12:00:00"
  }
}
```

### 4. 更新站点

**Endpoint**: `PUT /api/v1/sites/{site_id}`

**Request Body** (所有字段可选):

```json
{
  "name": "New Name",
  "theme": "modern-minimal",
  "is_active": true,
  "settings": {
    "custom_setting": "value"
  }
}
```

### 5. 删除站点

**Endpoint**: `DELETE /api/v1/sites/{site_id}`

**说明**: 软删除，标记为非激活状态，不真正删除数据。

**Response**:

```json
{
  "success": true,
  "message": "Site deactivated successfully"
}
```

### 6. 获取站点统计

**Endpoint**: `GET /api/v1/sites/{site_id}/stats`

**Response**:

```json
{
  "success": true,
  "data": {
    "site_id": 1,
    "site_name": "My Blog",
    "articles": 150,
    "categories": 20,
    "created_at": "2026-05-01T12:00:00"
  }
}
```

---

## 🔧 配置示例

### Nginx 配置（子域名模式）

```nginx
server {
    listen 80;
    server_name ~^(?<subdomain>.+)\.example\.com$;
    
    location / {
        proxy_pass http://localhost:9421;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Nginx 配置（路径模式）

```nginx
server {
    listen 80;
    server_name example.com;
    
    location / {
        proxy_pass http://localhost:9421;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Apache .htaccess

```apache
RewriteEngine On

# 子域名模式
RewriteCond %{HTTP_HOST} ^(.+)\.example\.com$
RewriteRule ^(.*)$ http://localhost:9421/$1 [P,L]

# 路径模式
RewriteRule ^(.*)$ http://localhost:9421/$1 [P,L]
```

---

## 💡 使用场景

### 场景 1: 多语言博客

- **站点 1**: `en.example.com` - English Blog
- **站点 2**: `zh.example.com` - 中文博客
- **站点 3**: `ja.example.com` - 日本語ブログ

**优势**:

- 每个语言独立管理
- 共享用户系统
- 统一后台管理

### 场景 2: 多品牌博客

- **站点 1**: `brand1.example.com` - Brand A Blog
- **站点 2**: `brand2.example.com` - Brand B Blog
- **站点 3**: `brand3.example.com` - Brand C Blog

**优势**:

- 独立主题和 branding
- 独立内容策略
- 共享技术栈

### 场景 3: SaaS 平台

- **客户 1**: `customer1.platform.com`
- **客户 2**: `customer2.platform.com`
- **客户 3**: `customer3.platform.com`

**优势**:

- 数据完全隔离
- 独立配置
- 统一管理

---

## 🛡️ 数据隔离

### 隔离级别

| 数据类型 | 隔离方式       | 说明       |
|------|------------|----------|
| 文章   | site_id 过滤 | 每个站点独立文章 |
| 分类   | site_id 过滤 | 每个站点独立分类 |
| 标签   | site_id 过滤 | 每个站点独立标签 |
| 评论   | 关联文章       | 跟随文章隔离   |
| 媒体   | 可选隔离       | 可共享或独立   |
| 用户   | 共享         | 跨站点登录    |
| 插件   | 独立配置       | 每个站点独立设置 |
| 主题   | 独立         | 每个站点独立主题 |

### 查询示例

```python
# 自动过滤当前站点的数据
from src.middleware.site_detection import get_current_site

site = get_current_site(request)

# 查询当前站点的文章
stmt = select(Article).where(
    Article.site_id == site.id,
    Article.status == 'published'
)
```

---

## 🎨 主题管理

每个站点可以独立设置主题：

```bash
# 更新站点主题
curl -X PUT "http://localhost:9421/api/v1/sites/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "modern-minimal"
  }'
```

**可用主题**:

- `default` - 默认主题
- `magazine` - 杂志风格
- `modern-minimal` - 现代简约

---

## 👥 用户管理

### 共享用户系统

用户在所有站点间共享：

- 一次注册，全站通用
- 统一的权限管理
- 跨站点登录

### 站点管理员

可以为每个站点设置独立的管理员：

```bash
curl -X PUT "http://localhost:9421/api/v1/sites/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "admin_user_id": 5
  }'
```

---

## 📈 性能优化

### 1. 缓存站点配置

```python
from src.extensions import cache


async def get_site_config(site_id: int):
    cache_key = f"site_config:{site_id}"

    # 尝试从缓存获取
    config = await cache.get(cache_key)
    if config:
        return config

    # 从数据库查询
    site = await db.get(Site, site_id)
    config = site.settings

    # 存入缓存（1小时）
    await cache.set(cache_key, config, expire=3600)

    return config
```

### 2. 数据库索引

确保以下字段有索引：

- `sites.domain`
- `sites.slug`
- `sites.is_active`
- `articles.site_id`
- `categories.site_id`

---

## ⚠️ 注意事项

### 1. 默认站点

- 必须有一个默认站点（is_default=true）
- 当无法识别站点时，回退到默认站点
- 不能删除默认站点

### 2. 域名配置

- 确保 DNS 正确配置
- 支持通配符域名 (*.example.com)
- 本地开发可使用 hosts 文件

### 3. SSL 证书

- 子域名模式需要通配符 SSL 证书
- 或在每个站点单独配置 SSL

### 4. 媒体文件

- 默认共享媒体库
- 可按站点隔离（未来功能）

---

## 🔍 故障排除

### 问题 1: 站点无法访问

**检查**:

1. 站点是否激活 (is_active=true)
2. 域名配置是否正确
3. DNS 是否解析
4. Nginx/Apache 配置

### 问题 2: 数据显示混乱

**原因**: site_id 过滤失效

**解决**:

1. 检查中间件是否加载
2. 确认 request.state.site 存在
3. 验证查询中包含 site_id 过滤

### 问题 3: 跨站点登录失败

**原因**: Session/Cookie 配置问题

**解决**:

1. 检查 Cookie domain 设置
2. 确认 JWT token 有效
3. 验证用户权限

---

## 📚 最佳实践

### 1. 站点命名规范

- 使用清晰的 slug（如 `tech-blog`, `company-news`）
- 避免特殊字符
- 保持简短易记

### 2. 权限管理

- 为每个站点设置独立管理员
- 超级管理员仅用于系统管理
- 定期审查权限

### 3. 备份策略

- 定期备份整个数据库
- 或按站点分别备份
- 测试恢复流程

### 4. 监控

- 监控每个站点的性能
- 跟踪站点使用情况
- 设置告警阈值

---

## 🎯 未来规划

- [ ] 站点克隆功能
- [ ] 批量站点管理
- [ ] 站点模板系统
- [ ] 独立媒体库
- [ ] 站点迁移工具
- [ ] 高级统计分析

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
