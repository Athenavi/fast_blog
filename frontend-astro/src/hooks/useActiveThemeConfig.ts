'use client';

import {useQuery} from '@tanstack/react-query';
import {apiClient} from '@/lib/api/base-client';

export interface ActiveThemeInfo {
    slug: string;
    name: string;
}

export interface ActiveThemeConfig {
    config: Record<string, any>;
    theme: ActiveThemeInfo | null;
}

/**
 * 获取当前激活主题的配置（颜色、布局、排版等）
 * 前端组件通过此 hook 读取主题配置来控制渲染
 */
export function useActiveThemeConfig() {
    return useQuery<ActiveThemeConfig>({
        queryKey: ['active-theme-config'],
        queryFn: async () => {
            const res = await apiClient.get('/themes/active/config');
            return res.data;
        },
        staleTime: 60_000,       // 1分钟内不重新请求
        refetchOnWindowFocus: false,
    });
}

/**
 * 获取当前激活主题的 CSS
 * 用于动态注入到页面 head 中
 */
export function useActiveThemeCSS() {
    return useQuery({
        queryKey: ['active-theme-css'],
        queryFn: async () => {
            const res = await apiClient.get('/themes/active/css');
            return res.data?.css || '';
        },
        staleTime: 60_000,
        refetchOnWindowFocus: false,
    });
}
