/**
 * FastBlog API JavaScript/TypeScript SDK
 *
 * 完整的FastBlog博客系统API客户端
 */

import axios, {AxiosInstance} from 'axios';

// ============================================================================
// 类型定义
// ============================================================================

export interface AuthResponse {
    access_token: string;
    refresh_token?: string;
    token_type: string;
    expires_in?: number;
    user?: UserInfo;
}

export interface UserInfo {
    id: number;
    username: string;
    email: string;
    role?: string;
    bio?: string;
    profile_picture?: string;
}

export interface Article {
    id: number;
    title: string;
    slug: string;
    excerpt?: string;
    content?: string;
    cover_image?: string;
    tags?: string[];
    author?: UserInfo;
    category_id?: number;
    category_name?: string;
    views?: number;
    likes?: number;
    status?: number | string;
    created_at?: string;
    updated_at?: string;
}

export interface Category {
    id: number;
    name: string;
    slug: string;
    description?: string;
    parent_id?: number | null;
    article_count?: number;
    order?: number;
}

export interface MediaFile {
    id: number;
    filename: string;
    url: string;
    thumbnail_url?: string;
    size?: number;
    mime_type?: string;
    created_at?: string;
}

export interface Comment {
    id: number;
    content: string;
    article_id: number;
    user_id?: number;
    parent_id?: number | null;
    created_at?: string;
    updated_at?: string;
}

export interface DashboardStats {
    total_articles: number;
    published_articles: number;
    draft_articles: number;
    total_users: number;
    active_users: number;
    total_views: number;
    total_likes: number;
    total_comments: number;
    recent_articles?: Article[];
    popular_articles?: Article[];
    views_trend?: Array<{ date: string; views: number }>;
}

export interface Plugin {
    id: number;
    name: string;
    slug: string;
    version: string;
    description?: string;
    author?: string;
    active: boolean;
    installed: boolean;
    settings?: Record<string, any>;
}

export interface Theme {
    id: number;
    name: string;
    slug: string;
    version: string;
    description?: string;
    author?: string;
    active: boolean;
    screenshot?: string;
}

export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
    pagination?: {
        current_page: number;
        per_page: number;
        total: number;
        total_pages: number;
        has_next: boolean;
        has_prev: boolean;
    };
}

// ============================================================================
// SDK 配置
// ============================================================================

export interface SDKConfig {
    baseURL: string;
    timeout?: number;
    accessToken?: string;
    headers?: Record<string, string>;
}

// ============================================================================
// FastBlog SDK 主类
// ============================================================================

export class FastBlogSDK {
    private client: AxiosInstance;
    private accessToken: string | null = null;

    constructor(config: SDKConfig) {
        this.accessToken = config.accessToken || null;

        this.client = axios.create({
            baseURL: config.baseURL,
            timeout: config.timeout || 30000,
            headers: {
                'Content-Type': 'application/json',
                ...config.headers,
            },
        });

        // 请求拦截器 - 自动添加 Token
        this.client.interceptors.request.use((config) => {
            if (this.accessToken) {
                config.headers['Authorization'] = `Bearer ${this.accessToken}`;
            }
            return config;
        });

        // 响应拦截器 - 统一错误处理
        this.client.interceptors.response.use(
            (response) => response,
            (error) => {
                const message = error.response?.data?.error || error.message;
                return Promise.reject(new Error(`FastBlog API Error: ${message}`));
            }
        );
    }

    // 🔐 认证模块 Auth

    /**
     * 用户登录
     */
    async login(username: string, password: string): Promise<AuthResponse> {
        const response = await this.client.post<ApiResponse<AuthResponse>>('/auth/login', {
            username,
            password,
        });

        const data = response.data.data!;
        this.accessToken = data.access_token;

        return data;
    }

    /**
     * 刷新 Token
     */
    async refreshToken(): Promise<AuthResponse> {
        const response = await this.client.post<ApiResponse<AuthResponse>>('/auth/refresh');
        const data = response.data.data!;
        this.accessToken = data.access_token;
        return data;
    }

    /**
     * 登出
     */
    async logout(): Promise<void> {
        await this.client.post('/auth/logout');
        this.accessToken = null;
    }

    /**
     * 设置 Access Token
     */
    setAccessToken(token: string): void {
        this.accessToken = token;
    }

    // 📝 文章模块 Articles

    /**
     * 获取文章列表
     */
    async getArticles(params?: {
        page?: number;
        perPage?: number;
        search?: string;
        categoryId?: number;
        userId?: number;
        status?: string;
        orderBy?: string;
        order?: 'asc' | 'desc';
    }): Promise<ApiResponse<Article[]>> {
        const queryParams: Record<string, any> = {
            page: params?.page || 1,
            per_page: params?.perPage || 10,
        };

        if (params?.search) queryParams.search = params.search;
        if (params?.categoryId) queryParams.category_id = params.categoryId;
        if (params?.userId) queryParams.user_id = params.userId;
        if (params?.status) queryParams.status = params.status;
        if (params?.orderBy) queryParams.order_by = params.orderBy;
        if (params?.order) queryParams.order = params.order;

        const response = await this.client.get<ApiResponse<Article[]>>('/articles', {
            params: queryParams,
        });

        return response.data;
    }

    /**
     * 获取文章详情
     */
    async getArticle(id: number): Promise<ApiResponse<Article>> {
        const response = await this.client.get<ApiResponse<Article>>(`/articles/${id}`);
        return response.data;
    }

    /**
     * 创建文章
     */
    async createArticle(article: {
        title: string;
        slug?: string;
        excerpt?: string;
        content: string;
        categoryId?: number;
        tags?: string[];
        coverImage?: string;
        status?: string;
    }): Promise<ApiResponse<Article>> {
        const response = await this.client.post<ApiResponse<Article>>('/articles', {
            title: article.title,
            slug: article.slug,
            excerpt: article.excerpt,
            content: article.content,
            category_id: article.categoryId,
            tags: article.tags,
            cover_image: article.coverImage,
            status: article.status,
        });
        return response.data;
    }

    /**
     * 更新文章
     */
    async updateArticle(id: number, updates: Partial<Article>): Promise<ApiResponse<Article>> {
        const response = await this.client.put<ApiResponse<Article>>(`/articles/${id}`, updates);
        return response.data;
    }

    /**
     * 删除文章
     */
    async deleteArticle(id: number): Promise<ApiResponse<void>> {
        const response = await this.client.delete<ApiResponse<void>>(`/articles/${id}`);
        return response.data;
    }

    // 📂 分类模块 Categories

    /**
     * 获取分类列表
     */
    async getCategories(): Promise<ApiResponse<Category[]>> {
        const response = await this.client.get<ApiResponse<Category[]>>('/categories');
        return response.data;
    }

    /**
     * 创建分类
     */
    async createCategory(category: {
        name: string;
        slug?: string;
        description?: string;
        parentId?: number | null;
    }): Promise<ApiResponse<Category>> {
        const response = await this.client.post<ApiResponse<Category>>('/categories', {
            name: category.name,
            slug: category.slug,
            description: category.description,
            parent_id: category.parentId,
        });
        return response.data;
    }

    // 🖼️ 媒体模块 Media

    /**
     * 上传文件
     */
    async uploadFile(file: File | Blob, folder: string = 'uploads'): Promise<ApiResponse<MediaFile>> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('folder', folder);

        const response = await this.client.post<ApiResponse<MediaFile>>('/media/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    }

    /**
     * 获取媒体列表
     */
    async getMedia(page: number = 1, perPage: number = 20): Promise<ApiResponse<MediaFile[]>> {
        const response = await this.client.get<ApiResponse<MediaFile[]>>('/media', {
            params: {page, per_page: perPage},
        });
        return response.data;
    }

    // 👥 用户模块 Users

    /**
     * 获取当前用户信息
     */
    async getCurrentUser(): Promise<ApiResponse<UserInfo>> {
        const response = await this.client.get<ApiResponse<UserInfo>>('/users/me');
        return response.data;
    }

    /**
     * 获取用户列表
     */
    async getUsers(page: number = 1, perPage: number = 10): Promise<ApiResponse<UserInfo[]>> {
        const response = await this.client.get<ApiResponse<UserInfo[]>>('/users', {
            params: {page, per_page: perPage},
        });
        return response.data;
    }

    // 💬 评论模块 Comments

    /**
     * 获取文章评论
     */
    async getComments(articleId: number, page: number = 1, perPage: number = 20): Promise<ApiResponse<Comment[]>> {
        const response = await this.client.get<ApiResponse<Comment[]>>('/comments', {
            params: {article_id: articleId, page, per_page: perPage},
        });
        return response.data;
    }

    /**
     * 发表评论
     */
    async createComment(comment: {
        articleId: number;
        content: string;
        parentId?: number | null;
    }): Promise<ApiResponse<Comment>> {
        const response = await this.client.post<ApiResponse<Comment>>('/comments', {
            article_id: comment.articleId,
            content: comment.content,
            parent_id: comment.parentId,
        });
        return response.data;
    }

    // 📊 仪表板模块 Dashboard

    /**
     * 获取统计数据
     */
    async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
        const response = await this.client.get<ApiResponse<DashboardStats>>('/dashboard/stats');
        return response.data;
    }

    /**
     * 获取分析数据
     */
    async getDashboardAnalytics(days: number = 30): Promise<ApiResponse<any>> {
        const response = await this.client.get<ApiResponse<any>>('/dashboard/analytics', {
            params: {days},
        });
        return response.data;
    }

    // 🔌 插件模块 Plugins

    /**
     * 获取插件列表
     */
    async getPlugins(): Promise<ApiResponse<Plugin[]>> {
        const response = await this.client.get<ApiResponse<Plugin[]>>('/plugins');
        return response.data;
    }

    /**
     * 激活插件
     */
    async activatePlugin(slug: string): Promise<ApiResponse<void>> {
        const response = await this.client.post<ApiResponse<void>>(`/plugins/${slug}/activate`);
        return response.data;
    }

    /**
     * 停用插件
     */
    async deactivatePlugin(slug: string): Promise<ApiResponse<void>> {
        const response = await this.client.post<ApiResponse<void>>(`/plugins/${slug}/deactivate`);
        return response.data;
    }

    // 🎨 主题模块 Themes

    /**
     * 获取主题列表
     */
    async getThemes(): Promise<ApiResponse<Theme[]>> {
        const response = await this.client.get<ApiResponse<Theme[]>>('/themes');
        return response.data;
    }

    /**
     * 激活主题
     */
    async activateTheme(slug: string): Promise<ApiResponse<void>> {
        const response = await this.client.post<ApiResponse<void>>(`/themes/${slug}/activate`);
        return response.data;
    }

    // ⚙️ 设置模块 Settings

    /**
     * 获取系统设置
     */
    async getSettings(): Promise<ApiResponse<Record<string, any>>> {
        const response = await this.client.get<ApiResponse<Record<string, any>>>('/settings');
        return response.data;
    }

    /**
     * 更新设置
     */
    async updateSettings(updates: Record<string, any>): Promise<ApiResponse<void>> {
        const response = await this.client.put<ApiResponse<void>>('/settings', updates);
        return response.data;
    }

    // 🤖 AI 功能模块

    /**
     * 生成 AI 友好的元数据
     */
    async generateMetadata(title: string, content: string, excerpt?: string): Promise<ApiResponse<any>> {
        const response = await this.client.post<ApiResponse<any>>('/ai/metadata/generate', {
            title,
            content,
            excerpt,
        });
        return response.data;
    }
}

// ============================================================================
// 默认导出
// ============================================================================

export default FastBlogSDK;
