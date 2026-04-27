/**
 * 主题管理Hook
 * 用于在前端动态加载和应用主题
 */

import {useCallback, useEffect, useState} from 'react';

interface ThemeConfig {
    metadata: {
        name: string;
        slug: string;
        version: string;
        description: string;
        author: string;
    };
    config: {
        colors?: Record<string, string>;
        layout?: {
            sidebarPosition?: string;
            contentWidth?: string;
            showSidebar?: boolean;
            showToc?: boolean;
            tocPosition?: string;
            headerStyle?: string;
            footerStyle?: string;
        };
        typography?: {
            fontFamily?: string;
            codeFont?: string;
            fontSize?: string;
            lineHeight?: number;
            headingWeight?: number;
            headingLetterSpacing?: string;
        };
        components?: {
            borderRadius?: string;
            shadowStyle?: string;
            buttonStyle?: string;
        };
        features?: {
            showComments?: boolean;
            showShareButtons?: boolean;
            showRelatedPosts?: boolean;
            showTableOfContents?: boolean;
            enableDarkMode?: boolean;
            autoDarkMode?: boolean;
            showCodeLineNumbers?: boolean;
            showCopyButton?: boolean;
            showReadingTime?: boolean;
            showWordCount?: boolean;
            showAuthorBox?: boolean;
            smoothScroll?: boolean;
            lazyLoadImages?: boolean;
            showFeaturedPosts?: boolean;
            featuredPostsCount?: number;
            showCategorySections?: boolean;
            stickyHeader?: boolean;
            breakingNewsBar?: boolean;
        };
    };
}

interface ThemeData {
    config: ThemeConfig | null;
    cssVariables: string;
    stylesheetUrl: string;
    isLoading: boolean;
    error: string | null;
}

export function useTheme() {
    const [themeData, setThemeData] = useState<ThemeData>({
        config: null,
        cssVariables: '',
        stylesheetUrl: '',
        isLoading: true,
        error: null,
    });

    // 加载主题配置
    const loadTheme = useCallback(async () => {
        try {
            setThemeData(prev => ({...prev, isLoading: true, error: null}));

            // 使用完整的后端 API URL
            const config = await import('@/lib/config');
            const apiConfig = config.getConfig();
            const apiUrl = `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/themes/active/config`;

            console.log('[useTheme] 请求主题配置:', apiUrl);
            const response = await fetch(apiUrl);
            const result = await response.json();

            console.log('[useTheme] API响应:', result);

            if (result.success && result.data.config) {
                setThemeData({
                    config: result.data.config,
                    cssVariables: result.data.css_variables || '',
                    stylesheetUrl: result.data.stylesheet_url || '',
                    isLoading: false,
                    error: null,
                });

                // 应用CSS变量（样式表由 ThemeProvider 统一加载）
                applyCssVariables(result.data.css_variables);
            } else {
                setThemeData(prev => ({
                    ...prev,
                    isLoading: false,
                    error: result.error || '加载主题失败',
                }));
            }
        } catch (error) {
            setThemeData(prev => ({
                ...prev,
                isLoading: false,
                error: error instanceof Error ? error.message : '未知错误',
            }));
        }
    }, []);

    // 应用CSS变量到document
    const applyCssVariables = (cssVariables: string) => {
        if (!cssVariables) return;

        let styleElement = document.getElementById('theme-variables') as HTMLStyleElement;

        if (!styleElement) {
            styleElement = document.createElement('style');
            styleElement.id = 'theme-variables';
            document.head.appendChild(styleElement);
        }

        styleElement.textContent = cssVariables;
    };

    // 动态加载样式表
    const loadStylesheet = (url: string) => {
        let linkElement = document.getElementById('theme-stylesheet') as HTMLLinkElement;

        if (!linkElement) {
            linkElement = document.createElement('link');
            linkElement.id = 'theme-stylesheet';
            linkElement.rel = 'stylesheet';
            document.head.appendChild(linkElement);
        }

        linkElement.href = url;
    };

    // 初始化时加载主题
    useEffect(() => {
        loadTheme();
    }, [loadTheme]);

    // 获取主题配置值
    const getThemeValue = (path: string): any => {
        if (!themeData.config) return undefined;

        const keys = path.split('.');
        let value: any = themeData.config;

        for (const key of keys) {
            if (value === undefined || value === null) return undefined;
            value = value[key];
        }

        return value;
    };

    return {
        ...themeData,
        loadTheme,
        getThemeValue,
    };
}

export default useTheme;
