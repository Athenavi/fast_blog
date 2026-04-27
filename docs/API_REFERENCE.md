# FastBlog API 参考文档

本文档提供 FastBlog 系统的核心 API 参考。完整的 API 文档可通过 Swagger UI 访问：http://localhost:9421/docs

## 📋 目录

- [认证](#认证)
- [文章管理](#文章管理)
- [分类和标签](#分类和标签)
- [用户管理](#用户管理)
- [评论系统](#评论系统)
- [媒体管理](#媒体管理)
- [错误码说明](#错误码说明)

---

## 🔐 认证

### 获取 Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### 使用 Token

在所有需要认证的请求中添加 Header：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 📝 文章管理

### 获取文章列表

```http
GET /api/v1/articles?page=1&per_page=10&order_by=created_at&order=desc
```

**查询参数:**
- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 10）
- `order_by`: 排序字段（created_at, updated_at, view_count）
- `order`: 排序方向（asc, desc）
- `category_id`: 分类 ID 过滤
- `tag`: 标签过滤
- `search`: 搜索关键词

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
GET /api/v1/articles/{id}
```

### 创建文章

```http
POST /api/v1/articles
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
  "status": 1
}
```

### 更新文章

```http
PUT /api/v1/articles/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "更新后的标题",
  "content": "更新后的内容"
}
```

### 删除文章

```http
DELETE /api/v1/articles/{id}
Authorization: Bearer {token}
```

---

## 🏷️ 分类和标签

### 获取分类列表

```http
GET /api/v1/categories
```

### 创建分类

```http
POST /api/v1/categories
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
GET /api/v1/tags
```

### 创建标签

```http
POST /api/v1/tags
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
GET /api/v1/users/me
Authorization: Bearer {token}
```

### 更新用户信息

```http
PUT /api/v1/users/me
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "bio": "个人简介"
}
```

### 获取用户列表（管理员）

```http
GET /api/v1/users?page=1&per_page=10
Authorization: Bearer {token}
```

---

## 💬 评论系统

### 获取文章评论

```http
GET /api/v1/articles/{article_id}/comments
```

### 发表评论

```http
POST /api/v1/articles/{article_id}/comments
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "评论内容",
  "parent_id": null
}
```

### 删除评论

```http
DELETE /api/v1/comments/{comment_id}
Authorization: Bearer {token}
```

---

## 🖼️ 媒体管理

### 上传文件

```http
POST /api/v1/media/upload
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
GET /api/v1/media?page=1&per_page=10
Authorization: Bearer {token}
```

### 删除媒体

```http
DELETE /api/v1/media/{media_id}
Authorization: Bearer {token}
```

---

## ⚙️ 设置管理

### 获取网站设置

```http
GET /api/v1/settings
```

### 更新网站设置（管理员）

```http
PUT /api/v1/settings
Authorization: Bearer {token}
Content-Type: application/json

{
  "site_name": "我的博客",
  "site_description": "一个现代化的博客系统",
  "site_url": "https://example.com"
}
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

## 📚 完整 API 文档

以上仅列出了核心 API 端点。完整的 API 文档包括：

- 插件管理 API
- 主题管理 API
- SEO 相关 API
- 数据分析 API
- Widget 管理 API

请访问 Swagger UI 查看完整文档：http://localhost:9421/docs

或使用 ReDoc：http://localhost:9421/redoc
