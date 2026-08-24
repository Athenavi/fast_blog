# FastBlog 移动端 API (v3)

移动端专用的 RESTful API，提供优化的数据传输和简化的响应结构。

**适用版本**: FastBlog V0.5.26.0612+

## 基础信息

```
Base URL: /api/v3
认证: Authorization: Bearer <token>
分页: page / per_page（默认 20，最大 50）
时间格式: ISO 8601
错误格式: {"success": false, "error": "描述"}
```

## 模块

### 认证 (`/api/v3/auth`)

| 方法   | 端点               | 说明           |
|------|------------------|--------------|
| POST | `/auth/login`    | 登录（支持用户名或邮箱） |
| POST | `/auth/register` | 注册           |

### 文章 (`/api/v3/articles`)

| 方法  | 端点                 | 说明            |
|-----|--------------------|---------------|
| GET | `/articles/list`   | 列表（支持分类/搜索过滤） |
| GET | `/articles/{id}`   | 详情            |
| GET | `/articles/search` | 搜索            |

### 评论 (`/api/v3/comments`)

| 方法   | 端点                       | 说明      |
|------|--------------------------|---------|
| GET  | `/comments/article/{id}` | 文章评论列表  |
| POST | `/comments/`             | 发表评论    |
| POST | `/comments/{id}/like`    | 点赞/取消点赞 |

### 用户 (`/api/v3/users`)

| 方法  | 端点               | 说明   |
|-----|------------------|------|
| GET | `/users/profile` | 获取资料 |
| PUT | `/users/profile` | 更新资料 |
| GET | `/users/stats`   | 用户统计 |

### 媒体 (`/api/v3/media`)

| 方法   | 端点                            | 说明             |
|------|-------------------------------|----------------|
| POST | `/media/upload/image`         | 上传图片（限制 10MB）  |
| POST | `/media/upload/article-cover` | 上传文章封面（限制 5MB） |

### 分类 (`/api/v3/categories`)

| 方法  | 端点                 | 说明   |
|-----|--------------------|------|
| GET | `/categories/list` | 分类列表 |

## 错误码

| 状态码 | 说明            |
|-----|---------------|
| 400 | 请求参数错误        |
| 401 | 未认证或 token 无效 |
| 403 | 权限不足          |
| 404 | 资源不存在         |
| 500 | 服务器内部错误       |
