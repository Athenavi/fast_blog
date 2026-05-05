"""
FastBlog API Python 客户端示例

本文件提供完整的 API 调用示例，支持同步和异步调用
需要安装: pip install httpx aiohttp
"""

from typing import Optional, Dict, Any


# ============================================================================
# 同步客户端 (使用 httpx)
# ============================================================================

class FastBlogClient:
    """FastBlog API 同步客户端"""

    def __init__(self, base_url: str = "http://localhost:9421/api/v1"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.session = None

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        import httpx

        url = f"{self.base_url}{endpoint}"

        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    # 🔐 认证 Auth

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        data = self._request("POST", "/auth/login", json={
            "username": username,
            "password": password
        })
        self.access_token = data.get("access_token")
        print("✅ Login successful")
        return data

    def refresh_token(self) -> Dict[str, Any]:
        """刷新 Token"""
        return self._request("POST", "/auth/refresh")

    def logout(self) -> None:
        """登出"""
        self._request("POST", "/auth/logout")
        self.access_token = None
        print("✅ Logout successful")

    # 📝 文章 Articles

    def get_articles(
            self,
            page: int = 1,
            per_page: int = 10,
            search: Optional[str] = None,
            category_id: Optional[int] = None,
            user_id: Optional[int] = None,
            status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取文章列表"""
        params = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        if category_id:
            params["category_id"] = category_id
        if user_id:
            params["user_id"] = user_id
        if status:
            params["status"] = status

        return self._request("GET", "/articles", params=params)

    def get_article(self, article_id: int) -> Dict[str, Any]:
        """获取文章详情"""
        return self._request("GET", f"/articles/{article_id}")

    def create_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """创建文章"""
        return self._request("POST", "/articles", json=article)

    def update_article(self, article_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新文章"""
        return self._request("PUT", f"/articles/{article_id}", json=updates)

    def delete_article(self, article_id: int) -> Dict[str, Any]:
        """删除文章"""
        return self._request("DELETE", f"/articles/{article_id}")

    # 📂 分类 Categories

    def get_categories(self) -> Dict[str, Any]:
        """获取分类列表"""
        return self._request("GET", "/categories")

    def create_category(self, category: Dict[str, Any]) -> Dict[str, Any]:
        """创建分类"""
        return self._request("POST", "/categories", json=category)

    # 🖼️ 媒体 Media

    def upload_file(self, file_path: str, folder: str = "uploads") -> Dict[str, Any]:
        """上传文件"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"folder": folder}
            return self._request("POST", "/media/upload", files=files, data=data)

    def get_media(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取媒体列表"""
        return self._request("GET", "/media", params={"page": page, "per_page": per_page})

    # 👥 用户 Users

    def get_current_user(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        return self._request("GET", "/users/me")

    def get_users(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """获取用户列表"""
        return self._request("GET", "/users", params={"page": page, "per_page": per_page})

    # 💬 评论 Comments

    def get_comments(self, article_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取文章评论"""
        return self._request("GET", "/comments", params={
            "article_id": article_id,
            "page": page,
            "per_page": per_page
        })

    def create_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """发表评论"""
        return self._request("POST", "/comments", json=comment)

    # 📊 仪表板 Dashboard

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        return self._request("GET", "/dashboard/stats")

    def get_dashboard_analytics(self, days: int = 30) -> Dict[str, Any]:
        """获取分析数据"""
        return self._request("GET", "/dashboard/analytics", params={"days": days})

    # 🔌 插件 Plugins

    def get_plugins(self) -> Dict[str, Any]:
        """获取插件列表"""
        return self._request("GET", "/plugins")

    def activate_plugin(self, slug: str) -> Dict[str, Any]:
        """激活插件"""
        return self._request("POST", f"/plugins/{slug}/activate")

    def deactivate_plugin(self, slug: str) -> Dict[str, Any]:
        """停用插件"""
        return self._request("POST", f"/plugins/{slug}/deactivate")

    # 🎨 主题 Themes

    def get_themes(self) -> Dict[str, Any]:
        """获取主题列表"""
        return self._request("GET", "/themes")

    def activate_theme(self, slug: str) -> Dict[str, Any]:
        """激活主题"""
        return self._request("POST", f"/themes/{slug}/activate")

    # ⚙️ 设置 Settings

    def get_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        return self._request("GET", "/settings")

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新设置"""
        return self._request("PUT", "/settings", json=updates)

    # 🤖 AI 功能

    def generate_metadata(
            self,
            title: str,
            content: str,
            excerpt: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成 AI 友好的元数据"""
        return self._request("POST", "/ai/metadata/generate", json={
            "title": title,
            "content": content,
            "excerpt": excerpt
        })


# ============================================================================
# 异步客户端 (使用 aiohttp)
# ============================================================================

class AsyncFastBlogClient:
    """FastBlog API 异步客户端"""

    def __init__(self, base_url: str = "http://localhost:9421/api/v1"):
        self.base_url = base_url
        self.access_token: Optional[str] = None

    async def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""

        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        import aiohttp

        url = f"{self.base_url}{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                    method=method,
                    url=url,
                    headers=await self._get_headers(),
                    **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()

    # 🔐 认证 Auth

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        data = await self._request("POST", "/auth/login", json={
            "username": username,
            "password": password
        })
        self.access_token = data.get("access_token")
        print("✅ Login successful")
        return data

    async def logout(self) -> None:
        """登出"""
        await self._request("POST", "/auth/logout")
        self.access_token = None
        print("✅ Logout successful")

    # 📝 文章 Articles

    async def get_articles(self, **params) -> Dict[str, Any]:
        """获取文章列表"""
        return await self._request("GET", "/articles", params=params)

    async def get_article(self, article_id: int) -> Dict[str, Any]:
        """获取文章详情"""
        return await self._request("GET", f"/articles/{article_id}")

    async def create_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """创建文章"""
        return await self._request("POST", "/articles", json=article)

    async def update_article(self, article_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新文章"""
        return await self._request("PUT", f"/articles/{article_id}", json=updates)

    async def delete_article(self, article_id: int) -> Dict[str, Any]:
        """删除文章"""
        return await self._request("DELETE", f"/articles/{article_id}")

    # 📊 仪表板 Dashboard

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        return await self._request("GET", "/dashboard/stats")


# ============================================================================
# 使用示例
# ============================================================================

def sync_example():
    """同步客户端使用示例"""
    print("=" * 60)
    print("同步客户端示例")
    print("=" * 60)

    # 创建客户端
    client = FastBlogClient()

    try:
        # 1. 登录
        print("\n📝 Logging in...")
        client.login("admin@example.com", "your_password")

        # 2. 获取文章列表
        print("\n📚 Fetching articles...")
        articles = client.get_articles(page=1, per_page=5)
        print(f"Found {len(articles['data'])} articles")

        # 3. 创建新文章
        print("\n✍️ Creating new article...")
        new_article = client.create_article({
            "title": "My First Article",
            "slug": "my-first-article",
            "excerpt": "This is a test article",
            "content": "# Hello World\n\nThis is my first article using the API!",
            "category_id": 1,
            "tags": ["Test", "API"],
            "status": "draft"
        })
        print(f"Article created with ID: {new_article['data']['id']}")

        # 4. 获取文章详情
        print("\n📖 Fetching article details...")
        article = client.get_article(new_article['data']['id'])
        print(f"Article title: {article['data']['title']}")

        # 5. 更新文章
        print("\n🔄 Updating article...")
        client.update_article(new_article['data']['id'], {
            "title": "Updated Title",
            "status": "published"
        })
        print("Article updated")

        # 6. 获取统计数据
        print("\n📊 Fetching dashboard stats...")
        stats = client.get_dashboard_stats()
        print(f"Total articles: {stats['data']['total_articles']}")

        # 7. 登出
        print("\n👋 Logging out...")
        client.logout()

        print("\n✅ Workflow completed successfully!")

    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")


async def async_example():
    """异步客户端使用示例"""
    print("=" * 60)
    print("异步客户端示例")
    print("=" * 60)

    # 创建客户端
    client = AsyncFastBlogClient()

    try:
        # 1. 登录
        print("\n📝 Logging in...")
        await client.login("admin@example.com", "your_password")

        # 2. 获取文章列表
        print("\n📚 Fetching articles...")
        articles = await client.get_articles(page=1, per_page=5)
        print(f"Found {len(articles['data'])} articles")

        # 3. 获取统计数据
        print("\n📊 Fetching dashboard stats...")
        stats = await client.get_dashboard_stats()
        print(f"Total articles: {stats['data']['total_articles']}")

        # 4. 登出
        print("\n👋 Logging out...")
        await client.logout()

        print("\n✅ Async workflow completed successfully!")

    except Exception as e:
        print(f"\n❌ Async workflow failed: {e}")


if __name__ == "__main__":
    # 运行同步示例
    sync_example()

    # 运行异步示例
    import asyncio

    asyncio.run(async_example())
