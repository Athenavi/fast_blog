# FastBlog API cURL 示例
# 
# 本文档提供所有核心 API 端点的 cURL 调用示例
# 复制命令到终端即可直接运行

# ============================================================================
# 配置变量
# ============================================================================
BASE_URL="http://localhost:9421/api/v1"
USERNAME="admin@example.com"
PASSWORD="your_password"

# ============================================================================
# 🔐 认证 Auth
# ============================================================================

# 1. 登录获取 Token
echo "=== 登录 ==="
curl -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'${USERNAME}'",
    "password": "'${PASSWORD}'"
  }' | jq .

# 保存 token（实际使用时替换 YOUR_TOKEN）
TOKEN="YOUR_ACCESS_TOKEN_HERE"

# 2. 刷新 Token
echo "=== 刷新 Token ==="
curl -X POST "${BASE_URL}/auth/refresh" \
  -H "Authorization: Bearer ${TOKEN}"

# 3. 登出
echo "=== 登出 ==="
curl -X POST "${BASE_URL}/auth/logout" \
  -H "Authorization: Bearer ${TOKEN}"

# ============================================================================
# 📝 文章 Articles
# ============================================================================

# 4. 获取文章列表
echo "=== 获取文章列表 ==="
curl -X GET "${BASE_URL}/articles?page=1&per_page=10&order_by=created_at&order=desc"

# 5. 搜索文章
echo "=== 搜索文章 ==="
curl -X GET "${BASE_URL}/articles?search=Python&page=1&per_page=10"

# 6. 按分类筛选
echo "=== 按分类筛选 ==="
curl -X GET "${BASE_URL}/articles?category_id=1&page=1&per_page=10"

# 7. 获取文章详情
echo "=== 获取文章详情 ==="
curl -X GET "${BASE_URL}/articles/1"

# 8. 创建文章（需要认证）
echo "=== 创建文章 ==="
curl -X POST "${BASE_URL}/articles" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的第一篇文章",
    "slug": "my-first-article",
    "excerpt": "这是文章的简短描述...",
    "content": "# 标题\n\n这是文章内容，支持 **Markdown** 语法。",
    "category_id": 1,
    "tags": ["Python", "教程"],
    "cover_image": "/media/covers/example.jpg",
    "status": "draft"
  }' | jq .

# 9. 更新文章
echo "=== 更新文章 ==="
curl -X PUT "${BASE_URL}/articles/1" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "更新后的标题",
    "content": "更新后的内容...",
    "status": "published"
  }' | jq .

# 10. 删除文章
echo "=== 删除文章 ==="
curl -X DELETE "${BASE_URL}/articles/1" \
  -H "Authorization: Bearer ${TOKEN}"

# ============================================================================
# 📂 分类 Categories
# ============================================================================

# 11. 获取分类列表
echo "=== 获取分类列表 ==="
curl -X GET "${BASE_URL}/categories"

# 12. 创建分类
echo "=== 创建分类 ==="
curl -X POST "${BASE_URL}/categories" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术教程",
    "slug": "tech-tutorials",
    "description": "编程和技术相关教程",
    "parent_id": null
  }' | jq .

# ============================================================================
# 🖼️ 媒体 Media
# ============================================================================

# 13. 上传文件
echo "=== 上传文件 ==="
curl -X POST "${BASE_URL}/media/upload" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@/path/to/image.jpg" \
  -F "folder=articles/2026/04" | jq .

# 14. 获取媒体列表
echo "=== 获取媒体列表 ==="
curl -X GET "${BASE_URL}/media?page=1&per_page=20"

# ============================================================================
# 👥 用户 Users
# ============================================================================

# 15. 获取当前用户信息
echo "=== 获取当前用户 ==="
curl -X GET "${BASE_URL}/users/me" \
  -H "Authorization: Bearer ${TOKEN}"

# 16. 获取用户列表
echo "=== 获取用户列表 ==="
curl -X GET "${BASE_URL}/users?page=1&per_page=10" \
  -H "Authorization: Bearer ${TOKEN}"

# ============================================================================
# 💬 评论 Comments
# ============================================================================

# 17. 获取文章评论
echo "=== 获取文章评论 ==="
curl -X GET "${BASE_URL}/comments?article_id=1&page=1&per_page=20"

# 18. 发表评论
echo "=== 发表评论 ==="
curl -X POST "${BASE_URL}/comments" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": 1,
    "content": "这是一条评论",
    "parent_id": null
  }' | jq .

# ============================================================================
# 📊 仪表板 Dashboard
# ============================================================================

# 19. 获取统计数据
echo "=== 获取统计数据 ==="
curl -X GET "${BASE_URL}/dashboard/stats" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# 20. 获取分析数据
echo "=== 获取分析数据 ==="
curl -X GET "${BASE_URL}/dashboard/analytics?days=30" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# ============================================================================
# 🔌 插件 Plugins
# ============================================================================

# 21. 获取插件列表
echo "=== 获取插件列表 ==="
curl -X GET "${BASE_URL}/plugins" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# 22. 激活插件
echo "=== 激活插件 ==="
curl -X POST "${BASE_URL}/plugins/seo-optimizer/activate" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# 23. 停用插件
echo "=== 停用插件 ==="
curl -X POST "${BASE_URL}/plugins/seo-optimizer/deactivate" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# ============================================================================
# 🎨 主题 Themes
# ============================================================================

# 24. 获取主题列表
echo "=== 获取主题列表 ==="
curl -X GET "${BASE_URL}/themes" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# 25. 激活主题
echo "=== 激活主题 ==="
curl -X POST "${BASE_URL}/themes/default/activate" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# ============================================================================
# ⚙️ 设置 Settings
# ============================================================================

# 26. 获取系统设置
echo "=== 获取系统设置 ==="
curl -X GET "${BASE_URL}/settings" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

# 27. 更新设置
echo "=== 更新设置 ==="
curl -X PUT "${BASE_URL}/settings" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "site_title": "My Blog",
    "site_description": "A wonderful blog"
  }' | jq .

# ============================================================================
# 🤖 AI 元数据生成
# ============================================================================

# 28. 生成 AI 友好的元数据
echo "=== 生成 AI 元数据 ==="
curl -X POST "${BASE_URL}/ai/metadata/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "FastAPI 入门教程",
    "content": "# FastAPI 入门\n\nFastAPI 是一个现代 Web 框架...",
    "excerpt": "本文介绍 FastAPI 的基本用法"
  }' | jq .

# ============================================================================
# 📡 RSS Feed
# ============================================================================

# 29. 获取 RSS Feed
echo "=== 获取 RSS Feed ==="
curl -X GET "http://localhost:9421/feed/rss"

# 30. 获取 Atom Feed
echo "=== 获取 Atom Feed ==="
curl -X GET "http://localhost:9421/feed/atom"

# ============================================================================
# 🔍 健康检查
# ============================================================================

# 31. 系统健康检查
echo "=== 健康检查 ==="
curl -X GET "http://localhost:9421/health" | jq .

# ============================================================================
# 使用提示
# ============================================================================
# 
# 1. 安装 jq（JSON 处理器）以获得更好的输出格式：
#    - macOS: brew install jq
#    - Ubuntu: sudo apt-get install jq
#    - Windows: choco install jq
#
# 2. 将 TOKEN 替换为实际的访问令牌
#
# 3. 使用环境变量管理敏感信息：
#    export BASE_URL="http://localhost:9421/api/v1"
#    export TOKEN="your_token_here"
#
# 4. 批量测试所有接口：
#    bash api_examples.sh
#
# ============================================================================
