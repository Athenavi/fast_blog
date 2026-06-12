# FastBlog API 参考文档

本文档提供 FastBlog 系统的 **API v2** 核心参考。完整的 API 文档可通过 Swagger UI 访问：http://localhost:9421/docs

> **注意**: 本项目当前使用 API v2 作为主要版本。v1 已完全删除，所有 v1 路径不再可用。

## 📋 目录

- [认证](#认证)
- [文章管理](#文章管理)
- [分类和标签](#分类和标签)
- [用户管理](#用户管理)
- [评论系统](#评论系统)
- [媒体管理](#媒体管理)
- [仪表板](#仪表板)
- [SEO](#seo)
- [系统管理](#系统管理)
- [错误码说明](#错误码说明)
- [快速示例](#快速示例)

---

## 🔐 认证

### 登录获取 Token

```bash
curl -X POST "http://localhost:9421/api/v2/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

> 登录支持 `username` 或 `email` 字段。

**Python 示例:**

```python
import requests

response = requests.post("http://localhost:9421/api/v2/auth/login",
                         json={"username": "admin", "password": "admin123"})
token = response.json()["data"]["access_token"]
```

**响应:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
      "expires_in": 3600,
      "user": {
          "id": 1,
          "username": "admin",
          "email": "admin@example.com",
          "role": "admin"
      }
  }
}
```

### 用户注册

```bash
curl -X POST "http://localhost:9421/api/v2/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "email": "user@example.com", "password": "securepass123"}'
```

### 使用 Token

在所有需要认证的请求中添加 Header：
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

系统同时支持 Cookie 和 Bearer Token 两种认证方式。

### 刷新 Token

```http
POST /api/v2/auth/refresh
Authorization: Bearer {token}
```

### 登出

```http
POST /api/v2/auth/logout
Authorization: Bearer {token}
```

---

## 📝 文章管理

### 获取文章列表

```http
GET /api/v2/articles?page=1&per_page=10&order_by=created_at&order=desc
```

**查询参数:**
- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 10）
- `order_by`: 排序字段（created_at, updated_at, view_count）
- `order`: 排序方向（asc, desc）
- `category_id`: 分类 ID 过滤
- `tag`: 标签过滤
- `search`: 搜索关键词
- `status`: 文章状态（draft, published）

**响应:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "title": "文章标题",
        "slug": "article-slug",
        "excerpt": "文章摘要...",
        "cover_image": "https://example.com/cover.jpg",
        "view_count": 100,
        "created_at": "2024-01-15T10:30:00Z",
        "author": {
          "id": 1,
          "username": "admin"
        },
        "categories": [
          {"id": 1, "name": "技术", "slug": "tech"}
        ],
        "tags": ["Python", "FastAPI"]
      }
    ],
    "pagination": {
      "current_page": 1,
      "per_page": 10,
      "total": 50,
      "total_pages": 5
    }
  }
}
```

### 获取文章详情

```http
GET /api/v2/articles/{id}
```

### 创建文章

```http
POST /api/v2/articles
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "新文章标题",
  "slug": "new-article",
  "content": "# Markdown 内容",
  "excerpt": "文章摘要",
  "cover_image": "https://example.com/cover.jpg",
  "category_ids": [1, 2],
  "tags": ["Python", "Tutorial"],
  "status": "published"
}
```

### 更新文章

```http
PUT /api/v2/articles/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "更新后的标题",
  "content": "更新后的内容"
}
```

### 删除文章

```http
DELETE /api/v2/articles/{id}
Authorization: Bearer {token}
```

### 搜索文章

```http
GET /api/v2/search?q=关键词&page=1&per_page=10
```

### 获取文章评论

```http
GET /api/v2/comments?article_id={article_id}&page=1&per_page=20
```

### 发表评论

```http
POST /api/v2/comments
Authorization: Bearer {token}
Content-Type: application/json

{
  "article_id": 1,
  "content": "评论内容",
  "parent_id": null
}
```

---

## 🏷️ 分类和标签

### 获取分类列表

```http
GET /api/v2/categories
```

### 创建分类

```http
POST /api/v2/categories
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "技术",
  "slug": "tech",
  "description": "技术相关文章"
}
```

### 获取标签列表

```http
GET /api/v2/tags
```

### 创建标签

```http
POST /api/v2/tags
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Python",
  "slug": "python"
}
```

---

## 👥 用户管理

### 获取当前用户信息

```http
GET /api/v2/users/me
Authorization: Bearer {token}
```

### 更新用户信息

```http
PUT /api/v2/users/me
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "bio": "个人简介"
}
```

### 获取用户列表（管理员）

```http
GET /api/v2/users?page=1&per_page=10
Authorization: Bearer {token}
```

---

## 💬 评论系统

### 获取文章评论

```http
GET /api/v2/comments?article_id={article_id}
```

### 发表评论

```http
POST /api/v2/comments
Authorization: Bearer {token}
Content-Type: application/json

{
  "article_id": 1,
  "content": "评论内容",
  "parent_id": null
}
```

### 删除评论

```http
DELETE /api/v2/comments/{comment_id}
Authorization: Bearer {token}
```

---

## 🖼️ 媒体管理

### 上传文件

```http
POST /api/v2/media/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary>
```

**响应:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "url": "https://example.com/media/file.jpg",
    "filename": "file.jpg",
    "size": 102400,
    "mime_type": "image/jpeg"
  }
}
```

### 获取媒体列表

```http
GET /api/v2/media?page=1&per_page=10
Authorization: Bearer {token}
```

### 删除媒体

```http
DELETE /api/v2/media/{media_id}
Authorization: Bearer {token}
```

---

## 📊 仪表板

### 获取仪表板统计

```http
GET /api/v2/dashboard/stats
Authorization: Bearer {token}
```

**响应:**

```json
{
    "success": true,
    "data": {
        "total_articles": 150,
        "published_articles": 120,
        "draft_articles": 30,
        "total_users": 50,
        "total_views": 15000,
        "total_comments": 300
    }
}
```

---

## 🔍 SEO

### 获取 SEO 信息

```http
GET /api/v2/seo/management
Authorization: Bearer {token}
```

### 获取 Sitemap

```http
GET /api/v2/seo/sitemap
```

### SEO 追踪数据

```http
GET /api/v2/seo/tracking?days=30
Authorization: Bearer {token}
```

---

## ⚙️ 系统管理

### 健康检查

```http
GET /api/v2/health
```

### 获取系统信息

```http
GET /api/v2/system/version/full
```

### 插件管理

```http
# 获取插件列表
GET /api/v2/plugins

# 启用插件
POST /api/v2/plugins/{slug}/enable
Authorization: Bearer {token}

# 禁用插件
POST /api/v2/plugins/{slug}/disable
Authorization: Bearer {token}
```

---

## ❌ 错误码说明

### 常见错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

### 错误码列表

| 错误码                       | HTTP 状态码 | 说明           |
|---------------------------|----------|--------------|
| `VALIDATION_ERROR`        | 422      | 请求参数验证失败     |
| `AUTHENTICATION_REQUIRED` | 401      | 需要认证         |
| `INVALID_TOKEN`           | 401      | Token 无效或已过期 |
| `PERMISSION_DENIED`       | 403      | 权限不足         |
| `NOT_FOUND`               | 404      | 资源不存在        |
| `DUPLICATE_ENTRY`         | 409      | 重复的数据        |
| `INTERNAL_ERROR`          | 500      | 服务器内部错误      |

---

## 💡 快速示例

### Python 完整示例

```python
import requests

BASE_URL = "http://localhost:9421/api/v2"

# 1. 登录获取token
response = requests.post(f"{BASE_URL}/auth/login",
                         json={"username": "admin", "password": "admin123"})
token = response.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. 获取文章列表
response = requests.get(f"{BASE_URL}/articles",
                        params={"page": 1, "per_page": 10}, headers=headers)
articles = response.json()

# 3. 创建文章
response = requests.post(f"{BASE_URL}/articles",
                         headers=headers,
                         json={
                             "title": "My Article",
                             "content": "# Hello World",
                             "status": "published"
                         })

# 4. 获取文章详情
article_id = 1
response = requests.get(f"{BASE_URL}/articles/{article_id}")
article = response.json()

# 5. 搜索文章
response = requests.get(f"{BASE_URL}/search",
                        params={"q": "Python", "page": 1, "per_page": 10})
results = response.json()

# 6. 获取仪表板统计
response = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
stats = response.json()
```

### JavaScript 完整示例

```javascript
const BASE_URL = 'http://localhost:9421/api/v2';

// 1. 登录获取token
const loginResponse = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: 'admin', password: 'admin123'})
});
const {data: {access_token}} = await loginResponse.json();

// 2. 获取文章列表
const articlesResponse = await fetch(`${BASE_URL}/articles?page=1&per_page=10`, {
    headers: {'Authorization': `Bearer ${access_token}`}
});
const articles = await articlesResponse.json();

// 3. 创建文章
const createResponse = await fetch(`${BASE_URL}/articles`, {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'My Article',
        content: '# Hello World',
        status: 'published'
    })
});
```

### cURL 快速测试

```bash
# 登录
TOKEN=$(curl -s -X POST "http://localhost:9421/api/v2/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.data.access_token')

# 获取文章列表
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:9421/api/v2/articles?page=1&per_page=5"

# 创建文章
curl -X POST "http://localhost:9421/api/v2/articles" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Article", "content": "# Hello", "status": "published"}'
```

---

## 📚 完整 API 文档

以上仅列出了核心 API 端点。完整的 API 文档包括：

- 仪表板统计与分析
- 插件管理
- 主题管理
- SEO 优化工具
- 电商功能（商品、订单、购物车）
- 通知系统
- 聊天与消息
- 协作编辑
- 翻译管理
- 广告管理
- 安全与权限管理
- 备份与恢复
- 性能监控

请访问 Swagger UI 查看完整文档：http://localhost:9421/docs

或使用 ReDoc：http://localhost:9421/redoc

---

## 📱 移动端 API (v3)

移动端使用独立的 API v3，详见 [移动端 API 文档](../src/api/v3/MOBILE_API_README.md)。

移动端 API 基础路径：`http://localhost:9421/api/v3/mobile/`

支持的模块：

- 认证 (`/auth`)
- 文章 (`/articles`)
- 评论 (`/comments`)
- 用户 (`/users`)
- 媒体 (`/media`)
- 分类 (`/categories`)
