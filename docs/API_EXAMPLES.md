# FastBlog API 使用示例

本文档提供 FastBlog API 的完整使用示例，包括 Python、JavaScript 和 cURL 三种语言的调用方式。

## 基础信息

- **Base URL**: `http://localhost:9421/api/v1`
- **认证方式**: JWT Bearer Token
- **响应格式**: JSON

## 认证

### 登录获取 Token

**cURL:**

```bash
curl -X POST "http://localhost:9421/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

**Python:**

```python
import requests

response = requests.post(
    "http://localhost:9421/api/v1/auth/login",
    json={
        "username": "admin",
        "password": "your_password"
    }
)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        username: 'admin',
        password: 'your_password'
    })
});

const data = await response.json();
const token = data.access_token;
```

---

## 文章 API

### 1. 获取文章列表

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/articles?page=1&per_page=10&status=published"
```

**Python:**

```python
import requests

response = requests.get(
    "http://localhost:9421/api/v1/articles",
    params={
        "page": 1,
        "per_page": 10,
        "status": "published"
    }
)

articles = response.json()
print(f"Total: {articles['total']}")
for article in articles['items']:
    print(f"- {article['title']}")
```

**JavaScript:**

```javascript
const params = new URLSearchParams({
    page: 1,
    per_page: 10,
    status: 'published'
});

const response = await fetch(`http://localhost:9421/api/v1/articles?${params}`);
const data = await response.json();

console.log(`Total: ${data.total}`);
data.items.forEach(article => {
    console.log(`- ${article.title}`);
});
```

### 2. 获取文章详情

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/articles/1"
```

**Python:**

```python
import requests

response = requests.get("http://localhost:9421/api/v1/articles/1")
article = response.json()

print(f"Title: {article['title']}")
print(f"Author: {article['author']['username']}")
print(f"Views: {article['views']}")
print(f"Content: {article['content'][:200]}...")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/articles/1');
const article = await response.json();

console.log(`Title: ${article.title}`);
console.log(`Author: ${article.author.username}`);
console.log(`Views: ${article.views}`);
console.log(`Content: ${article.content.substring(0, 200)}...`);
```

### 3. 创建文章

**cURL:**

```bash
curl -X POST "http://localhost:9421/api/v1/articles" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Article",
    "slug": "my-first-article",
    "excerpt": "This is my first article",
    "content": "# Hello World\n\nThis is the content.",
    "category_id": 1,
    "tags": ["tutorial", "beginner"],
    "status": "published"
  }'
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.post(
    "http://localhost:9421/api/v1/articles",
    headers=headers,
    json={
        "title": "My First Article",
        "slug": "my-first-article",
        "excerpt": "This is my first article",
        "content": "# Hello World\n\nThis is the content.",
        "category_id": 1,
        "tags": ["tutorial", "beginner"],
        "status": "published"
    }
)

article = response.json()
print(f"Created article ID: {article['id']}")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/articles', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'My First Article',
        slug: 'my-first-article',
        excerpt: 'This is my first article',
        content: '# Hello World\n\nThis is the content.',
        category_id: 1,
        tags: ['tutorial', 'beginner'],
        status: 'published'
    })
});

const article = await response.json();
console.log(`Created article ID: ${article.id}`);
```

### 4. 更新文章

**cURL:**

```bash
curl -X PUT "http://localhost:9421/api/v1/articles/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "content": "# Updated Content"
  }'
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.put(
    "http://localhost:9421/api/v1/articles/1",
    headers=headers,
    json={
        "title": "Updated Title",
        "content": "# Updated Content"
    }
)

print("Article updated successfully")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/articles/1', {
    method: 'PUT',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'Updated Title',
        content: '# Updated Content'
    })
});

console.log('Article updated successfully');
```

### 5. 删除文章

**cURL:**

```bash
curl -X DELETE "http://localhost:9421/api/v1/articles/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.delete(
    "http://localhost:9421/api/v1/articles/1",
    headers=headers
)

print("Article deleted successfully")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/articles/1', {
    method: 'DELETE',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    }
});

console.log('Article deleted successfully');
```

---

## 分类 API

### 1. 获取分类列表

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/categories"
```

**Python:**

```python
import requests

response = requests.get("http://localhost:9421/api/v1/categories")
categories = response.json()

for category in categories:
    print(f"- {category['name']} ({category['articles_count']} articles)")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/categories');
const categories = await response.json();

categories.forEach(category => {
    console.log(`- ${category.name} (${category.articles_count} articles)`);
});
```

### 2. 创建分类

**cURL:**

```bash
curl -X POST "http://localhost:9421/api/v1/categories" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technology",
    "slug": "technology",
    "description": "Tech articles"
  }'
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.post(
    "http://localhost:9421/api/v1/categories",
    headers=headers,
    json={
        "name": "Technology",
        "slug": "technology",
        "description": "Tech articles"
    }
)

category = response.json()
print(f"Created category ID: {category['id']}")
```

---

## 用户 API

### 1. 获取当前用户信息

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.get(
    "http://localhost:9421/api/v1/users/me",
    headers=headers
)

user = response.json()
print(f"Username: {user['username']}")
print(f"Email: {user['email']}")
print(f"VIP Level: {user['vip_level']}")
```

**JavaScript:**

```javascript
const response = await fetch('http://localhost:9421/api/v1/users/me', {
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    }
});

const user = await response.json();
console.log(`Username: ${user.username}`);
console.log(`Email: ${user.email}`);
console.log(`VIP Level: ${user.vip_level}`);
```

### 2. 更新用户资料

**cURL:**

```bash
curl -X PUT "http://localhost:9421/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Hello, I am a blogger!",
    "locale": "en_US"
  }'
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.put(
    "http://localhost:9421/api/v1/users/me",
    headers=headers,
    json={
        "bio": "Hello, I am a blogger!",
        "locale": "en_US"
    }
)

print("Profile updated successfully")
```

---

## 评论 API

### 1. 获取文章评论

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/comments?article_id=1&page=1&per_page=20"
```

**Python:**

```python
import requests

response = requests.get(
    "http://localhost:9421/api/v1/comments",
    params={
        "article_id": 1,
        "page": 1,
        "per_page": 20
    }
)

comments = response.json()
for comment in comments['items']:
    print(f"{comment['author_name']}: {comment['content']}")
```

**JavaScript:**

```javascript
const params = new URLSearchParams({
    article_id: 1,
    page: 1,
    per_page: 20
});

const response = await fetch(`http://localhost:9421/api/v1/comments?${params}`);
const comments = await response.json();

comments.items.forEach(comment => {
    console.log(`${comment.author_name}: ${comment.content}`);
});
```

### 2. 发表评论

**cURL:**

```bash
curl -X POST "http://localhost:9421/api/v1/comments" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": 1,
    "content": "Great article!"
  }'
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.post(
    "http://localhost:9421/api/v1/comments",
    headers=headers,
    json={
        "article_id": 1,
        "content": "Great article!"
    }
)

comment = response.json()
print(f"Comment created with ID: {comment['id']}")
```

---

## 媒体 API

### 1. 上传文件

**cURL:**

```bash
curl -X POST "http://localhost:9421/api/v1/media/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

with open('/path/to/image.jpg', 'rb') as f:
    response = requests.post(
        "http://localhost:9421/api/v1/media/upload",
        headers=headers,
        files={"file": f}
    )

media = response.json()
print(f"File URL: {media['file_url']}")
```

**JavaScript (Node.js):**

```javascript
const FormData = require('form-data');
const fs = require('fs');

const form = new FormData();
form.append('file', fs.createReadStream('/path/to/image.jpg'));

const response = await fetch('http://localhost:9421/api/v1/media/upload', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        ...form.getHeaders()
    },
    body: form
});

const media = await response.json();
console.log(`File URL: ${media.file_url}`);
```

### 2. 获取媒体列表

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/media?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.get(
    "http://localhost:9421/api/v1/media",
    headers=headers,
    params={"page": 1, "per_page": 20}
)

media_list = response.json()
for media in media_list['items']:
    print(f"- {media['filename']} ({media['file_size']} bytes)")
```

---

## 搜索 API

### 搜索文章

**cURL:**

```bash
curl -X GET "http://localhost:9421/api/v1/search?q=python+tutorial&type=article"
```

**Python:**

```python
import requests

response = requests.get(
    "http://localhost:9421/api/v1/search",
    params={
        "q": "python tutorial",
        "type": "article"
    }
)

results = response.json()
print(f"Found {results['total']} results")
for result in results['items']:
    print(f"- {result['title']}")
```

**JavaScript:**

```javascript
const params = new URLSearchParams({
    q: 'python tutorial',
    type: 'article'
});

const response = await fetch(`http://localhost:9421/api/v1/search?${params}`);
const results = await response.json();

console.log(`Found ${results.total} results`);
results.items.forEach(result => {
    console.log(`- ${result.title}`);
});
```

---

## 错误处理

所有 API 响应都遵循统一的错误格式：

```json
{
  "success": false,
  "error": "Error message",
  "detail": "Detailed error information"
}
```

**Python 错误处理示例:**

```python
import requests

try:
    response = requests.get("http://localhost:9421/api/v1/articles/999")
    response.raise_for_status()
    article = response.json()
except requests.exceptions.HTTPError as e:
    error_data = e.response.json()
    print(f"Error: {error_data['error']}")
```

**JavaScript 错误处理示例:**

```javascript
try {
    const response = await fetch('http://localhost:9421/api/v1/articles/999');

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error);
    }

    const article = await response.json();
} catch (error) {
    console.error(`Error: ${error.message}`);
}
```

---

## 高级用法

### 1. 分页遍历所有文章

**Python:**

```python
import requests


def get_all_articles():
    all_articles = []
    page = 1
    per_page = 100

    while True:
        response = requests.get(
            "http://localhost:9421/api/v1/articles",
            params={"page": page, "per_page": per_page}
        )
        data = response.json()

        all_articles.extend(data['items'])

        if len(all_articles) >= data['total']:
            break

        page += 1

    return all_articles


articles = get_all_articles()
print(f"Total articles: {len(articles)}")
```

### 2. 批量创建文章

**Python:**

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}

articles_data = [
    {"title": "Article 1", "content": "Content 1"},
    {"title": "Article 2", "content": "Content 2"},
    {"title": "Article 3", "content": "Content 3"},
]

for article_data in articles_data:
    response = requests.post(
        "http://localhost:9421/api/v1/articles",
        headers=headers,
        json=article_data
    )

    if response.status_code == 200:
        print(f"✓ Created: {article_data['title']}")
    else:
        print(f"✗ Failed: {article_data['title']} - {response.json()['error']}")
```

### 3. 实时监控文章浏览量

**Python:**

```python
import requests
import time


def monitor_article_views(article_id, interval=60):
    """每 interval 秒检查一次文章浏览量"""
    while True:
        response = requests.get(f"http://localhost:9421/api/v1/articles/{article_id}")
        article = response.json()

        print(f"[{time.strftime('%H:%M:%S')}] Views: {article['views']}")

        time.sleep(interval)


# 监控文章 ID 为 1 的浏览量
monitor_article_views(1)
```

---

## 最佳实践

### 1. 使用会话保持连接

**Python:**

```python
import requests

session = requests.Session()
session.headers.update({"Authorization": "Bearer YOUR_TOKEN"})

# 复用连接，提高性能
response1 = session.get("http://localhost:9421/api/v1/articles")
response2 = session.get("http://localhost:9421/api/v1/categories")
```

### 2. 添加请求超时

**Python:**

```python
import requests

try:
    response = requests.get(
        "http://localhost:9421/api/v1/articles",
        timeout=5  # 5秒超时
    )
except requests.exceptions.Timeout:
    print("Request timed out")
```

**JavaScript:**

```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);

try {
    const response = await fetch('http://localhost:9421/api/v1/articles', {
        signal: controller.signal
    });
} catch (error) {
    if (error.name === 'AbortError') {
        console.error('Request timed out');
    }
} finally {
    clearTimeout(timeoutId);
}
```

### 3. 缓存 API 响应

**Python:**

```python
from functools import lru_cache
import requests


@lru_cache(maxsize=100)
def get_article(article_id):
    response = requests.get(f"http://localhost:9421/api/v1/articles/{article_id}")
    return response.json()


# 第一次调用会发起请求
article1 = get_article(1)

# 第二次调用直接使用缓存
article2 = get_article(1)
```

---

## 相关资源

- [API 完整文档](http://localhost:9421/docs) - Swagger UI
- [日志系统文档](./LOGGING_SYSTEM.md)
- [数据库索引优化](./DATABASE_INDEX_OPTIMIZATION.md)
- [SQL 注入防护](./SQL_INJECTION_PROTECTION.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
