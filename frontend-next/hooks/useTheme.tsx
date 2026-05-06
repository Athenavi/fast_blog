/**
 * 主题管理Hook - 重构版
 * 极简设计，避免无限循环
 */

import {createContext, useContext, useEffect, useState} from 'react';

interface ThemeConfig {
    metadata?: {
        name: string;
        slug: string;
        version: string;
        description: string;
        author: string;
    };
    config?: {
        colors?: Record<string, string>;
        layout?: any;
        typography?: any;
        components?: any;
        features?: any;
    };
}

interface ThemeData {
    config: ThemeConfig | null;
    cssVariables: string;
    stylesheetUrl: string;
    isLoading: boolean;
    error: string | null;
}

interface ThemeContextType extends ThemeData {
}

// 创建 Context
export const ThemeContext = createContext<ThemeContextType | null>(null);

// 简单的 useTheme hook
export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
}

// Provider 组件
export function ThemeDataProvider({children}: { children: React.ReactNode }) {
    const [themeData, setThemeData] = useState<ThemeData>({
        config: null,
        cssVariables: '',
        stylesheetUrl: '',
        isLoading: true,
        error: null,
    });

    useEffect(() => {
        let mounted = true;

        async function loadTheme() {
            try {
                const config = await import('@/lib/config');
                const apiConfig = config.getConfig();
                const apiUrl = `${apiConfig.API_BASE_URL}${apiConfig.API_PREFIX}/themes/active/config`;

                const response = await fetch(apiUrl);
                const result = await response.json();

                if (!mounted) return;

                if (result.success && result.data.config) {
                    let stylesheetUrl = result.data.stylesheet_url || '';
                    if (stylesheetUrl && stylesheetUrl.startsWith('/')) {
                        stylesheetUrl = `${apiConfig.API_BASE_URL}${stylesheetUrl}`;
                    }

                    setThemeData({
                        config: result.data.config,
                        cssVariables: result.data.css_variables || '',
                        stylesheetUrl: stylesheetUrl,
                        isLoading: false,
                        error: null,
                    });
                } else {
                    setThemeData(prev => ({
                        ...prev,
                        isLoading: false,
                        error: result.error || '加载主题失败',
                    }));
                }
            } catch (error) {
                if (!mounted) return;
                setThemeData(prev => ({
                    ...prev,
                    isLoading: false,
                    error: error instanceof Error ? error.message : '未知错误',
                }));
            }
        }

        loadTheme();

        return () => {
            mounted = false;
        };
    }, []);

    return (
        <ThemeContext.Provider value={themeData}>
            {children}
        </ThemeContext.Provider>
    );
}
