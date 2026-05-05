/**
 * FastBlog API JavaScript 客户端示例
 *
 * 本文件提供完整的 API 调用示例，可直接在浏览器或 Node.js 环境中运行
 */

// ============================================================================
// 配置
// ============================================================================
const BASE_URL = 'http://localhost:9421/api/v1';
let accessToken = '';

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 发送 HTTP 请求
 */
async function request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    // 添加认证 token
    if (accessToken) {
        config.headers['Authorization'] = `Bearer ${accessToken}`;
    }

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Request Failed: ${endpoint}`, error);
        throw error;
    }
}

// ============================================================================
// 🔐 认证 Auth
// ============================================================================

/**
 * 用户登录
 */
async function login(username, password) {
    const data = await request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({username, password}),
    });

    accessToken = data.access_token;
    console.log('✅ Login successful');
    return data;
}

/**
 * 刷新 Token
 */
async function refreshToken() {
    return await request('/auth/refresh', {
        method: 'POST',
    });
}

/**
 * 登出
 */
async function logout() {
    await request('/auth/logout', {
        method: 'POST',
    });
    accessToken = '';
    console.log('✅ Logout successful');
}

// ============================================================================
// 📝 文章 Articles
// ============================================================================

/**
 * 获取文章列表
 */
async function getArticles(params = {}) {
    const {page = 1, perPage = 10, search, categoryId, userId, status} = params;

    const queryParams = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
    });

    if (search) queryParams.append('search', search);
    if (categoryId) queryParams.append('category_id', categoryId.toString());
    if (userId) queryParams.append('user_id', userId.toString());
    if (status) queryParams.append('status', status);

    return await request(`/articles?${queryParams}`);
}

/**
 * 获取文章详情
 */
async function getArticle(id) {
    return await request(`/articles/${id}`);
}

/**
 * 创建文章
 */
async function createArticle(article) {
    return await request('/articles', {
        method: 'POST',
        body: JSON.stringify(article),
    });
}

/**
 * 更新文章
 */
async function updateArticle(id, updates) {
    return await request(`/articles/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

/**
 * 删除文章
 */
async function deleteArticle(id) {
    return await request(`/articles/${id}`, {
        method: 'DELETE',
    });
}

// ============================================================================
// 📂 分类 Categories
// ============================================================================

/**
 * 获取分类列表
 */
async function getCategories() {
    return await request('/categories');
}

/**
 * 创建分类
 */
async function createCategory(category) {
    return await request('/categories', {
        method: 'POST',
        body: JSON.stringify(category),
    });
}

// ============================================================================
// 🖼️ 媒体 Media
// ============================================================================

/**
 * 上传文件
 */
async function uploadFile(file, folder = 'uploads') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);

    const response = await fetch(`${BASE_URL}/media/upload`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
        },
        body: formData,
    });

    return await response.json();
}

/**
 * 获取媒体列表
 */
async function getMedia(page = 1, perPage = 20) {
    return await request(`/media?page=${page}&per_page=${perPage}`);
}

// ============================================================================
// 👥 用户 Users
// ============================================================================

/**
 * 获取当前用户信息
 */
async function getCurrentUser() {
    return await request('/users/me');
}

/**
 * 获取用户列表
 */
async function getUsers(page = 1, perPage = 10) {
    return await request(`/users?page=${page}&per_page=${perPage}`);
}

// ============================================================================
// 💬 评论 Comments
// ============================================================================

/**
 * 获取文章评论
 */
async function getComments(articleId, page = 1, perPage = 20) {
    return await request(`/comments?article_id=${articleId}&page=${page}&per_page=${perPage}`);
}

/**
 * 发表评论
 */
async function createComment(comment) {
    return await request('/comments', {
        method: 'POST',
        body: JSON.stringify(comment),
    });
}

// ============================================================================
// 📊 仪表板 Dashboard
// ============================================================================

/**
 * 获取统计数据
 */
async function getDashboardStats() {
    return await request('/dashboard/stats');
}

/**
 * 获取分析数据
 */
async function getDashboardAnalytics(days = 30) {
    return await request(`/dashboard/analytics?days=${days}`);
}

// ============================================================================
// 🔌 插件 Plugins
// ============================================================================

/**
 * 获取插件列表
 */
async function getPlugins() {
    return await request('/plugins');
}

/**
 * 激活插件
 */
async function activatePlugin(slug) {
    return await request(`/plugins/${slug}/activate`, {
        method: 'POST',
    });
}

/**
 * 停用插件
 */
async function deactivatePlugin(slug) {
    return await request(`/plugins/${slug}/deactivate`, {
        method: 'POST',
    });
}

// ============================================================================
// 🎨 主题 Themes
// ============================================================================

/**
 * 获取主题列表
 */
async function getThemes() {
    return await request('/themes');
}

/**
 * 激活主题
 */
async function activateTheme(slug) {
    return await request(`/themes/${slug}/activate`, {
        method: 'POST',
    });
}

// ============================================================================
// ⚙️ 设置 Settings
// ============================================================================

/**
 * 获取系统设置
 */
async function getSettings() {
    return await request('/settings');
}

/**
 * 更新设置
 */
async function updateSettings(updates) {
    return await request('/settings', {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

// ============================================================================
// 🤖 AI 功能
// ============================================================================

/**
 * 生成 AI 友好的元数据
 */
async function generateMetadata(title, content, excerpt = null) {
    return await request('/ai/metadata/generate', {
        method: 'POST',
        body: JSON.stringify({title, content, excerpt}),
    });
}

// ============================================================================
// 使用示例
// ============================================================================

/**
 * 完整工作流程示例
 */
async function exampleWorkflow() {
    try {
        // 1. 登录
        console.log('📝 Logging in...');
        await login('admin@example.com', 'your_password');

        // 2. 获取文章列表
        console.log('\n📚 Fetching articles...');
        const articles = await getArticles({page: 1, perPage: 5});
        console.log(`Found ${articles.data.length} articles`);

        // 3. 创建新文章
        console.log('\n✍️ Creating new article...');
        const newArticle = await createArticle({
            title: 'My First Article',
            slug: 'my-first-article',
            excerpt: 'This is a test article',
            content: '# Hello World\n\nThis is my first article using the API!',
            category_id: 1,
            tags: ['Test', 'API'],
            status: 'draft',
        });
        console.log(`Article created with ID: ${newArticle.data.id}`);

        // 4. 获取文章详情
        console.log('\n📖 Fetching article details...');
        const article = await getArticle(newArticle.data.id);
        console.log(`Article title: ${article.data.title}`);

        // 5. 更新文章
        console.log('\n🔄 Updating article...');
        await updateArticle(newArticle.data.id, {
            title: 'Updated Title',
            status: 'published',
        });
        console.log('Article updated');

        // 6. 获取统计数据
        console.log('\n📊 Fetching dashboard stats...');
        const stats = await getDashboardStats();
        console.log(`Total articles: ${stats.data.total_articles}`);

        // 7. 登出
        console.log('\n👋 Logging out...');
        await logout();

        console.log('\n✅ Workflow completed successfully!');
    } catch (error) {
        console.error('❌ Workflow failed:', error.message);
    }
}

// ============================================================================
// 导出（Node.js 环境）
// ============================================================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // Auth
        login,
        refreshToken,
        logout,

        // Articles
        getArticles,
        getArticle,
        createArticle,
        updateArticle,
        deleteArticle,

        // Categories
        getCategories,
        createCategory,

        // Media
        uploadFile,
        getMedia,

        // Users
        getCurrentUser,
        getUsers,

        // Comments
        getComments,
        createComment,

        // Dashboard
        getDashboardStats,
        getDashboardAnalytics,

        // Plugins
        getPlugins,
        activatePlugin,
        deactivatePlugin,

        // Themes
        getThemes,
        activateTheme,

        // Settings
        getSettings,
        updateSettings,

        // AI
        generateMetadata,

        // Example
        exampleWorkflow,
    };
}

// 在浏览器中直接运行示例
if (typeof window !== 'undefined') {
    console.log('FastBlog API Client loaded');
    console.log('Run exampleWorkflow() to see a complete demo');
}
