# FastBlog Python SDK

FastBlog API V2 的官方 Python SDK，提供同步和异步客户端。

> **Python 要求**: 3.10+ | **API 版本**: V2 (`/api/v2/`)

## 安装

```bash
pip install fastblog-sdk
# 或从源码安装
cd sdk/python && pip install -e .
```

依赖：`requests`（同步）/ `aiohttp`（异步，可选）

## Quick Start

```python
from fastblog_sdk import FastBlogClient

client = FastBlogClient("http://localhost:9421/api/v2")
client.login("admin@example.com", "password")
articles = client.get_articles(page=1, per_page=10)

# 异步客户端
from fastblog_sdk import AsyncFastBlogClient
async with AsyncFastBlogClient("http://localhost:9421/api/v2") as client:
    await client.login("admin@example.com", "password")
    articles = await client.get_articles(page=1, per_page=10)
```

## API 方法

| 方法                                                                      | 说明      |
|-------------------------------------------------------------------------|---------|
| `login/logout/register`                                                 | 认证      |
| `get_articles/get_article/create_article/update_article/delete_article` | 文章 CRUD |
| `get_categories/create_category`                                        | 分类      |
| `get_current_user/update_profile`                                       | 用户      |
| `upload_media`                                                          | 媒体上传    |
| `get_dashboard_stats/get_dashboard_analytics`                           | 仪表板     |
| `get_seo_traffic/get_top_keywords/get_seo_dashboard`                    | SEO 追踪  |

## 运行测试

```bash
pip install pytest pytest-asyncio
pytest tests/
```

## License

MIT License
