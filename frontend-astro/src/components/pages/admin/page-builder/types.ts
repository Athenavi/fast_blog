/**
 * 页面构建器 — 共享类型
 *
 * 优先复用 @/lib/page-builder/nested-blocks 中的定义，
 * 这里只声明本模块特有的类型，避免重复。
 */

/** 后端返回的页面数据结构 */
export interface PageData {
    id: number;
    title: string;
    slug: string;
    blocks_data: any[];
    template_name?: string;
    is_published: boolean;
    created_at?: string;
    updated_at?: string;
}

/** 块样式快捷面板的单项 */
export interface StyleField {
    key: string;
    label: string;
    type: 'color' | 'number' | 'select';
    min?: number;
    max?: number;
    step?: number;
    options?: { label: string; value: string | number }[];
    defaultValue: any;
}

/** 组件库中一个条目（模板或单个组件） */
export interface LibraryItem {
    id?: string | number;
    name?: string;
    title?: string;
    category: string;
    description: string;
    blocks: Array<{ type: string; props?: Record<string, any> }>;
    preview_image?: string;
    default_data?: any;
}

/** 预览设备类型 */
export type PreviewDevice = 'desktop' | 'tablet' | 'mobile';
