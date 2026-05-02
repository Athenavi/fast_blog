'use client';

import React, {useCallback, useEffect} from 'react';
import {usePathname} from 'next/navigation';
import useTheme, {ThemeContext} from '@/hooks/useTheme';
import {applyThemeAdaptation} from '@/lib/theme-adapter';
import {darkModeManager} from '@/lib/dark-mode-manager';

interface ThemeProviderProps {
    children: React.ReactNode;
}

/**
 * 主题提供者组件
 * 确保所有页面都能正确加载和应用主题样式
 * 注意：/admin/* 路径下的页面会跳过主题加载
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({children}) => {
    // ✅ 在 TSX 文件中创建 Provider，调用 useTheme
    const theme = useTheme();

    return (
        <ThemeContext.Provider value={theme}>
            <ThemeProviderContent>{children}</ThemeProviderContent>
        </ThemeContext.Provider>
    );
};

// ✅ 内部组件，使用 Context
const ThemeProviderContent: React.FC<ThemeProviderProps> = ({children}) => {
    const pathname = usePathname();
    const isAdminPage = pathname?.startsWith('/admin');

    // ✅ 使用 Context，确保全局共享同一个实例
    const themeHook = React.useContext(ThemeContext);
    if (!themeHook) {
        throw new Error('ThemeProviderContent must be used within ThemeProvider');
    }
    
    const {cssVariables, stylesheetUrl, isLoading, config} = themeHook;

    // 注入全局样式覆盖（最高优先级）
    const injectGlobalStyleOverrides = useCallback((colors: Record<string, string>) => {
        // 只在客户端执行，避免服务端和客户端不一致
        if (typeof window === 'undefined') return;
        
        const styleId = 'theme-global-overrides';
        let styleElement = document.getElementById(styleId) as HTMLStyleElement;

        if (!styleElement) {
            styleElement = document.createElement('style');
            styleElement.id = styleId;
            // 确保在最后加载，优先级最高
            document.head.appendChild(styleElement);
        }

        const primary = colors.primary || '#3b82f6';
        const secondary = colors.secondary || '#64748b';
        const accent = colors.accent || '#f59e0b';
        const background = colors.background || '#ffffff';
        const foreground = colors.foreground || '#1f2937';

        // 使用更高的选择器优先级
        styleElement.textContent = `
            /* 全局主题覆盖 - 最高优先级 */
            body * {
                /* 强制所有渐变使用主题色 */
            }
            
            /* Hero区域的渐变背景 */
            section[class*="min-h"][class*="gradient"] {
                background: linear-gradient(to bottom right, ${primary}, ${accent}) !important;
            }
            
            /* 所有按钮的渐变 */
            button[class*="gradient"], a[class*="gradient"] {
                background: linear-gradient(to right, ${primary}, ${secondary}) !important;
            }
            
            /* 白色文字在彩色背景上保持白色 */
            section[class*="gradient"] h1,
            section[class*="gradient"] p,
            section[class*="gradient"] div {
                color: white !important;
            }
        `;
    }, []);

    // 应用主题样式表
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        // 只在客户端执行
        if (typeof window === 'undefined') return;

        if (stylesheetUrl) {
            let linkElement = document.getElementById('theme-stylesheet') as HTMLLinkElement;

            if (!linkElement) {
                linkElement = document.createElement('link');
                linkElement.id = 'theme-stylesheet';
                linkElement.rel = 'stylesheet';
                document.head.appendChild(linkElement);
            }

            // 只有当URL真正变化时才更新
            if (linkElement.href !== stylesheetUrl) {
                linkElement.href = stylesheetUrl;
            }
        }
    }, [stylesheetUrl, isAdminPage]);

    // 应用主题适配（将硬编码颜色映射到主题变量）
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        if (config && config.config) {
            const colors = config.config.colors || {};
            console.log('[ThemeProvider] 应用主题适配，颜色:', colors);
            applyThemeAdaptation(colors);

            // ✅ 移除 observeThemeChanges()，它会导致无限循环
            // observeThemeChanges();

            // 注入高优先级的全局样式覆盖
            injectGlobalStyleOverrides(colors);
        }
    }, [config, isAdminPage]); // ✅ 移除 injectGlobalStyleOverrides 依赖

    // 监听深色模式变化并重新应用主题
    useEffect(() => {
        // 如果是管理后台页面，不加载主题
        if (isAdminPage) return;

        const unsubscribe = darkModeManager.addListener(() => {
            if (config && config.config) {
                const colors = config.config.colors || {};
                console.log('[ThemeProvider] 深色模式变化，重新应用主题');
                applyThemeAdaptation(colors);
                injectGlobalStyleOverrides(colors);
            }
        });

        return unsubscribe;
    }, [config, isAdminPage]); // ✅ 移除 injectGlobalStyleOverrides 依赖

    // 如果是管理后台页面，直接渲染子组件，不加载主题
    if (isAdminPage) {
        return <>{children}</>;
    }

    // 如果正在加载主题，显示简单的加载状态
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        );
    }

    return (
        <>
            {/* 注入主题CSS变量 */}
            <style id="theme-variables" dangerouslySetInnerHTML={{__html: cssVariables}} suppressHydrationWarning/>
            {children}
        </>
    );
};

export default ThemeProvider;
