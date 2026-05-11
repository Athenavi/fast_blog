# FastBlog Python SDK

FastBlog API 的官方 Python SDK，提供同步和异步客户端。

## 安装

```bash
pip install fastblog-sdk
```

## 快速开始

### 同步客户端

```python
from fastblog_sdk import FastBlogClient

# 创建客户端
client = FastBlogClient("http://localhost:9421/api/v1")

# 登录
client.login("admin@example.com", "password")

# 获取文章列表
articles = client.get_articles(page=1, per_page=10)
print(f"找到 {len(articles['data'])} 篇文章")

# 创建文章
new_article = client.create_article({
    "title": "我的文章",
    "content": "# Hello World",
    "status": "draft"
})

# 登出
client.logout()
```

### 异步客户端

```python
import asyncio
from fastblog_sdk import AsyncFastBlogClient

async def main():
    # 创建客户端
    client = AsyncFastBlogClient("http://localhost:9421/api/v1")
    
    # 登录
    await client.login("admin@example.com", "password")
    
    # 获取文章
    articles = await client.get_articles(page=1, per_page=10)
    print(f"找到 {len(articles['data'])} 篇文章")
    
    # 登出
    await client.logout()

asyncio.run(main())
```

## 功能特性

- ✅ 完整的 API 覆盖（28+ 端点）
- ✅ 同步和异步客户端
- ✅ 自动 Token 管理
- ✅ 类型提示支持
- ✅ 详细的文档字符串
- ✅ 错误处理

## API 参考

完整 API 文档请访问：https://github.com/fastblog/fast_blog/docs

## License

MIT License
