/**
 * API 响应通用类型定义
 */

// API 响应基础结构
interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
    code?: number;
}

// 分页响应结构
interface PaginatedResponse<T = any> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

// 扩展 User 类型添加 role_id 字段
declare module '@/types/generated/api-types' {
    interface User {
        role_id?: number;
        avatar_url?: string;
        bio?: string;
        created_at?: string;
        updated_at?: string;
    }
}

// 主题组件类型声明
declare module '@/themes/magazine/components' {
    import {ComponentType} from 'react';

    export const MagazineLayout: ComponentType<{ children?: React.ReactNode }>;
    export const MagazineHeader: ComponentType;
    export const MagazineFooter: ComponentType;
    export const MagazineHomePage: ComponentType<any>;
    export const MagazineArticleCard: ComponentType<{ article: any }>;

    export const Layout: ComponentType<{ children?: React.ReactNode }>;
    export const Header: ComponentType;
    export const Footer: ComponentType;
    export const HomePage: ComponentType<any>;
    export const ArticleCard: ComponentType<{ article: any }>;

    const defaultExport: {
        Layout: ComponentType<{ children?: React.ReactNode }>;
        Header: ComponentType;
        Footer: ComponentType;
        HomePage: ComponentType<any>;
        ArticleCard: ComponentType<{ article: any }>;
    };
    export default defaultExport;
}

declare module '@/themes/modern-minimal/components' {
    import {ComponentType} from 'react';

    export const ModernMinimalLayout: ComponentType<{ children?: React.ReactNode }>;
    export const ModernMinimalHeader: ComponentType;
    export const ModernMinimalFooter: ComponentType;
    export const ModernMinimalHomePage: ComponentType<any>;
    export const ModernMinimalArticleCard: ComponentType<{ article: any }>;
    export const TableOfContents: ComponentType<any>;
    export const CodeBlock: ComponentType<any>;

    const defaultExport: {
        Layout: ComponentType<{ children?: React.ReactNode }>;
        Header: ComponentType;
        Footer: ComponentType;
        HomePage: ComponentType<any>;
        ArticleCard: ComponentType<{ article: any }>;
    };
    export default defaultExport;
}
