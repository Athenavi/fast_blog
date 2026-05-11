/**
 * API 响应类型定义
 */

// 通用 API 响应
export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
    items: T[];
    pagination: {
        page: number;
        page_size: number;
        total: number;
        total_pages: number;
    };
}

// 分类相关
export interface Category {
    id: number;
    name: string;
    slug: string;
    description?: string;
    parent_id?: number;
}

export interface CategoryListResponse {
    categories: Category[];
    total: number;
}

// 文章相关
export interface Article {
    id: number;
    title: string;
    slug: string;
    content?: string;
    excerpt?: string;
    cover_image?: string;
    thumbnail?: string;
    created_at: string;
    updated_at: string;
    comments?: Comment[];
    views_count?: number;
    view_count?: number; // 兼容旧字段名
}

export interface ArticleListResponse {
    articles: Article[];
    total: number;
    total_pages: number;
}

// 评论相关
export interface Comment {
    id: number;
    content: string;
    created_at: string;
}

export interface CommentListResponse {
    comments: Comment[];
    total: number;
    total_pages: number;
}

// 菜单相关
export interface MenuItem {
    id: number;
    title: string;
    url: string;
    children?: MenuItem[];
}

export interface MenuListResponse {
    menus: MenuItem[];
}

// 用户相关
export interface User {
    id: number;
    username: string;
    email: string;
    role_id?: number;
}

export interface UserListResponse {
    users: User[];
    total: number;
}

// 角色相关
export interface Role {
    id: number;
    name: string;
    slug: string;
    permissions?: string[];
}

export interface RoleListResponse {
    roles: Role[];
}

// 权限相关
export interface Permission {
    id: number;
    name: string;
    code: string;
}

export interface PermissionListResponse {
    permissions: Permission[];
}

// 插件相关
export interface Plugin {
    id: number;
    name: string;
    slug: string;
    version: string;
    is_active: boolean;
}

export interface PluginListResponse {
    plugins: Plugin[];
}

// 主题相关
export interface Theme {
    id: number;
    name: string;
    slug: string;
    is_active: boolean;
}

export interface ThemeListResponse {
    themes: Theme[];
}

// 语言相关
export interface Language {
    code: string;
    name: string;
    native_name: string;
}

export interface LanguageListResponse {
    languages: Language[];
}

// 翻译相关
export interface TranslationStats {
    [lang: string]: {
        total_translations: number;
        is_default: boolean;
        is_rtl: boolean;
    };
}

export interface TranslationListResponse {
    translations: Record<string, string>;
}

// SEO 分析
export interface SEOAnalysisResult {
    score: number;
    issues: string[];
    recommendations: string[];
}
